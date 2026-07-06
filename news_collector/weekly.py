from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import AppSettings
from .dashboard import load_catalog

WEEKLY_TOPIC = "Weekly Digest"


def collect_week_material(
    *,
    settings: AppSettings,
    root_dir: Path,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Compact view of the last `days` of generated reports for the LLM."""
    output_dir = root_dir / settings.output.directory
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    material: list[dict[str, Any]] = []
    for entry in load_catalog(output_dir):
        date = str(entry.get("date") or "")
        if date < cutoff:
            continue
        json_name = (entry.get("files") or {}).get("json")
        if not json_name:
            continue
        report_path = output_dir / str(json_name)
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        columns = []
        for column in report.get("columns") or []:
            stories = [
                {
                    "title": str(news.get("title") or ""),
                    "url": str(news.get("url") or ""),
                    "kind": str(news.get("kind") or "news"),
                    "summary": str(news.get("summary") or "")[:400],
                }
                for news in column.get("news_list") or []
                if isinstance(news, dict)
            ]
            if stories:
                columns.append({"column": str(column.get("title") or ""), "stories": stories})
        if columns:
            material.append(
                {
                    "date": date,
                    "report_title": str(report.get("report_title") or ""),
                    "topic": str(report.get("topic") or ""),
                    "tldr": report.get("tldr") or [],
                    "columns": columns,
                }
            )
    material.sort(key=lambda item: str(item.get("date")))
    return material


async def generate_weekly_digest(
    *,
    settings: AppSettings,
    root_dir: Path,
    logger: logging.Logger,
    days: int = 7,
    model_label: str = "weekly digest",
) -> dict[str, Any] | None:
    """Synthesize the week's reports into one digest report on disk.

    Returns the same result shape the daily flow produces, or None when
    there is no material to digest. Model settings must already be applied
    (instantiate DailyNewsCollector first or call its _configure_agently).
    """
    from workflow.common import DailyNewsChunkConfig, create_editor_agent, tone_instruction
    from workflow.report_chunks import _write_outputs

    from .markdown import render_markdown

    material = collect_week_material(settings=settings, root_dir=root_dir, days=days)
    if not material:
        logger.info("[Weekly] No reports found in the last %s days.", days)
        return None
    logger.info("[Weekly] Digesting %s daily reports.", len(material))

    now = datetime.now()
    digest = await (
        create_editor_agent(kind="chief")
        .load_yaml_prompt(
            root_dir / "prompts" / "write_weekly.yaml",
            mappings={
                "reports": material,
                "today": now.strftime("%Y-%m-%d"),
                "language": settings.workflow.output_language,
                "tone_instruction": tone_instruction(settings),
            },
        )
        .async_start(
            ensure_keys=[
                "report_title",
                "overview",
                "highlights[*].title",
                "highlights[*].url",
                "highlights[*].reason",
            ]
        )
    )
    if not isinstance(digest, dict):
        raise RuntimeError(f"Weekly digest generation failed: {digest!r}")

    report_title = str(digest.get("report_title") or f"Weekly Digest — {now.strftime('%Y-%m-%d')}")
    overview = str(digest.get("overview") or "").strip()
    news_list = []
    known_urls = {
        story["url"]: story
        for report in material
        for column in report["columns"]
        for story in column["stories"]
        if story.get("url")
    }
    for highlight in digest.get("highlights") or []:
        if not isinstance(highlight, dict):
            continue
        url = str(highlight.get("url") or "").strip()
        source_story = known_urls.get(url, {})
        news_list.append(
            {
                "title": str(highlight.get("title") or source_story.get("title") or ""),
                "url": url,
                "kind": source_story.get("kind", ""),
                "summary": str(highlight.get("reason") or "").strip(),
                "source": "Weekly Digest",
                "date": "",
            }
        )
    news_list = [news for news in news_list if news["title"] and news["url"]]

    columns = [
        {
            "title": "Highlights of the Week",
            "prologue": overview,
            "news_list": news_list,
        }
    ]
    render_args: dict[str, Any] = {
        "report_title": report_title,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "topic": WEEKLY_TOPIC,
        "language": settings.workflow.output_language,
        "columns": columns,
        "model_label": model_label,
        "tldr": [],
    }
    markdown = render_markdown(**render_args)
    chunk_config = DailyNewsChunkConfig(
        settings=settings,
        prompt_dir=root_dir / "prompts",
        output_dir=root_dir / settings.output.directory,
        model_label=model_label,
    )
    output_paths = _write_outputs(
        config=chunk_config,
        report_date=now.strftime("%Y-%m-%d"),
        markdown=markdown,
        render_args=render_args,
    )
    for output_format, path in output_paths.items():
        logger.info("[Weekly %s Saved] %s", output_format.capitalize(), path)
    return {
        "report_title": report_title,
        "output_path": output_paths["markdown"],
        "output_paths": output_paths,
        "markdown": markdown,
        "tldr": [],
        "columns": columns,
    }


__all__ = ["WEEKLY_TOPIC", "collect_week_material", "generate_weekly_digest"]
