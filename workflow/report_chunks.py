from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from agently import TriggerFlowRuntimeData

from news_collector.dashboard import update_dashboard
from news_collector.html_report import render_html
from news_collector.markdown import render_markdown

from .common import (
    DailyNewsChunkConfig,
    create_editor_agent,
    require_logger,
    safe_filename,
    strip_greeting,
    tone_instruction,
)


def create_prepare_request_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    async def prepare_request(data: TriggerFlowRuntimeData) -> dict[str, Any]:
        topic = str(data.value).strip()
        now = datetime.now()
        request = {
            "topic": topic,
            "today": now.strftime("%Y-%m-%d"),
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "language": config.settings.workflow.output_language,
        }
        data.state.set("request", request)
        require_logger(data).info("[Topic] %s", topic)
        return request

    return prepare_request


def create_generate_outline_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    async def generate_outline(data: TriggerFlowRuntimeData) -> list[dict[str, Any]]:
        request = data.value
        logger = require_logger(data)
        if config.settings.outline.use_customized:
            outline = _get_customized_outline(config)
            logger.info("[Use Customized Outline] %s", outline)
        else:
            outline = await _generate_outline(config, request)
            logger.info("[Outline Generated] %s", outline)
        data.state.set("outline", outline)
        return outline.get("column_list", [])

    return generate_outline


def create_render_report_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    async def render_report(data: TriggerFlowRuntimeData) -> dict[str, Any]:
        request = data.state.get("request") or {}
        outline = data.state.get("outline") or {}
        logger = require_logger(data)
        columns = _dedupe_columns(
            [column for column in data.value if isinstance(column, dict)]
        )
        report_title = str(
            outline.get("report_title")
            or f"Daily News about {request.get('topic', 'the topic')}"
        )
        tldr: list[str] = []
        if config.settings.summary.enable_tldr and columns:
            tldr = await _write_tldr(config, report_title, columns, logger)
        render_args: dict[str, Any] = {
            "report_title": report_title,
            "generated_at": str(request.get("generated_at") or ""),
            "topic": str(request.get("topic") or ""),
            "language": config.settings.workflow.output_language,
            "columns": columns,
            "model_label": config.model_label,
            "tldr": tldr,
        }
        markdown = render_markdown(**render_args)
        report_date = str(request.get("today") or "")
        output_paths = _write_outputs(
            config=config,
            report_date=report_date,
            markdown=markdown,
            render_args=render_args,
        )
        for output_format, path in output_paths.items():
            logger.info("[%s Saved] %s", output_format.capitalize(), path)
        if config.history is not None:
            published_news = [
                news
                for column in columns
                for news in column.get("news_list", [])
                if isinstance(news, dict)
            ]
            config.history.mark_published(
                published_news,
                date=report_date or datetime.now().strftime("%Y-%m-%d"),
            )
            config.history.save()
            logger.info("[History Updated] %s stories tracked", len(config.history))
        return {
            "report_title": report_title,
            "generated_at": str(request.get("generated_at") or ""),
            "topic": str(request.get("topic") or ""),
            "language": config.settings.workflow.output_language,
            "model": config.model_label,
            "output_path": output_paths["markdown"],
            "output_paths": output_paths,
            "markdown": markdown,
            "tldr": tldr,
            "columns": columns,
        }

    return render_report


def _dedupe_columns(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop stories that already appeared in an earlier column of this report."""
    seen_urls: set[str] = set()
    deduped_columns: list[dict[str, Any]] = []
    for column in columns:
        news_list = column.get("news_list")
        if not isinstance(news_list, list):
            deduped_columns.append(column)
            continue
        kept_news = []
        for news in news_list:
            url = str(news.get("url") or "").strip() if isinstance(news, dict) else ""
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            kept_news.append(news)
        if kept_news:
            deduped_columns.append({**column, "news_list": kept_news})
    return deduped_columns


async def _write_tldr(
    config: DailyNewsChunkConfig,
    report_title: str,
    columns: list[dict[str, Any]],
    logger: Any,
) -> list[str]:
    slimmed_columns = [
        {
            "column_title": column.get("title", ""),
            "stories": [
                {
                    "title": news.get("title", ""),
                    "summary": news.get("summary", ""),
                }
                for news in column.get("news_list", [])
                if isinstance(news, dict)
            ],
        }
        for column in columns
    ]
    try:
        tldr_result = await (
            create_editor_agent(kind="chief")
            .load_yaml_prompt(
                config.prompt_dir / "write_tldr.yaml",
                mappings={
                    "columns": slimmed_columns,
                    "report_title": report_title,
                    "language": config.settings.workflow.output_language,
                    "tone_instruction": tone_instruction(config.settings),
                },
            )
            .async_start(ensure_keys=["takeaways"])
        )
    except Exception as exc:
        logger.warning("[TLDR Failed] %s", exc)
        return []
    if not isinstance(tldr_result, dict):
        return []
    takeaways = tldr_result.get("takeaways")
    if not isinstance(takeaways, list):
        return []
    cleaned = [
        strip_greeting(str(item).strip())
        for item in takeaways
        if str(item or "").strip()
    ]
    if cleaned:
        logger.info("[TLDR Generated] %s takeaways", len(cleaned))
    return cleaned[:5]


async def _generate_outline(
    config: DailyNewsChunkConfig,
    request: dict[str, Any],
) -> dict[str, Any]:
    outline = await (
        create_editor_agent(kind="chief")
        .load_yaml_prompt(
            config.prompt_dir / "create_outline.yaml",
            mappings={
                "topic": request["topic"],
                "today": request["today"],
                "language": config.settings.workflow.output_language,
                "max_column_num": config.settings.workflow.max_column_num,
            },
        )
        .async_start(
            ensure_keys=[
                "report_title",
                "column_list[*].column_title",
                "column_list[*].column_requirement",
                "column_list[*].search_keywords",
            ]
        )
    )
    if not isinstance(outline, dict):
        raise TypeError(f"Invalid outline result: {outline}")
    column_list = outline.get("column_list", [])
    if not isinstance(column_list, list):
        raise TypeError("Outline column_list must be a list.")
    outline["column_list"] = column_list[: config.settings.workflow.max_column_num]
    return outline


def _get_customized_outline(config: DailyNewsChunkConfig) -> dict[str, Any]:
    outline = copy.deepcopy(config.settings.outline.customized)
    column_list = outline.get("column_list", [])
    if not isinstance(column_list, list) or not column_list:
        raise ValueError("Customized outline must provide a non-empty column_list.")
    outline["column_list"] = column_list[: config.settings.workflow.max_column_num]
    outline.setdefault("report_title", "Daily News Briefing")
    return outline


def _write_outputs(
    *,
    config: DailyNewsChunkConfig,
    report_date: str,
    markdown: str,
    render_args: dict[str, Any],
) -> dict[str, str]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    report_title = str(render_args["report_title"])
    base_name = f"{safe_filename(report_title)}_{report_date or datetime.now().strftime('%Y-%m-%d')}"

    output_paths: dict[str, str] = {}
    for output_format in config.settings.output.formats:
        if output_format == "markdown":
            content = markdown
            suffix = ".md"
        elif output_format == "json":
            content = json.dumps(
                {
                    "report_title": render_args["report_title"],
                    "generated_at": render_args["generated_at"],
                    "topic": render_args["topic"],
                    "language": render_args["language"],
                    "model": render_args["model_label"],
                    "tldr": render_args.get("tldr") or [],
                    "columns": render_args["columns"],
                },
                ensure_ascii=False,
                indent=2,
            )
            suffix = ".json"
        else:
            content = render_html(**render_args)
            suffix = ".html"
        output_path = config.output_dir / f"{base_name}{suffix}"
        output_path.write_text(content, encoding="utf-8")
        output_paths[output_format] = str(output_path)

    if config.settings.output.update_index:
        _update_report_index(
            config=config,
            report_title=report_title,
            report_date=report_date,
            markdown_file_name=f"{base_name}.md",
            topic=str(render_args["topic"]),
        )
    if config.settings.output.update_dashboard:
        update_dashboard(
            config.output_dir,
            {
                "report_title": report_title,
                "topic": str(render_args["topic"]),
                "language": str(render_args["language"]),
                "date": report_date or datetime.now().strftime("%Y-%m-%d"),
                "generated_at": str(render_args["generated_at"]),
                "files": {
                    output_format: Path(path).name
                    for output_format, path in output_paths.items()
                },
            },
        )
    return output_paths


def _update_report_index(
    *,
    config: DailyNewsChunkConfig,
    report_title: str,
    report_date: str,
    markdown_file_name: str,
    topic: str,
) -> None:
    index_path = config.output_dir / "INDEX.md"
    entry = (
        f"- {report_date or datetime.now().strftime('%Y-%m-%d')} — "
        f"[{report_title}](<./{markdown_file_name}>) — {topic}\n"
    )
    if index_path.exists():
        existing = index_path.read_text(encoding="utf-8")
        if entry in existing:
            return
        index_path.write_text(existing.rstrip("\n") + "\n" + entry, encoding="utf-8")
    else:
        index_path.write_text("# Generated Reports\n\n" + entry, encoding="utf-8")


__all__ = [
    "create_prepare_request_chunk",
    "create_generate_outline_chunk",
    "create_render_report_chunk",
]
