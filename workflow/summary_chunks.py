from __future__ import annotations

import copy
from typing import Any, Callable

from agently import TriggerFlowRuntimeData

from tools.content_quality import is_invalid_browse_content

from .common import (
    DailyNewsChunkConfig,
    create_editor_agent,
    is_chinese_language,
    reader_context,
    require_browse_tool,
    require_logger,
    safe_int,
    strip_greeting,
    tone_instruction,
)


def create_prepare_summary_candidates_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    async def prepare_summary_candidates(data: TriggerFlowRuntimeData):
        context = _coerce_summary_context(data.value)
        if context is None:
            data.state.set("summary_context", None, emit=False)
            data.state.set("summary_results", [], emit=False)
            data.state.set("summary_target_count", 0, emit=False)
            await data.async_emit("Summary.Done", None)
            return []

        candidates = build_summary_candidates(
            config,
            context["column_outline"],
            context["searched_news"],
            context["picked_news"],
        )
        target_count = min(
            len(context["picked_news"]),
            config.settings.workflow.max_news_per_column,
        )

        data.state.set("summary_context", copy.deepcopy(context), emit=False)
        data.state.set("summary_results", [], emit=False)
        data.state.set("summary_target_count", target_count, emit=False)

        if target_count <= 0 or not candidates:
            # An empty for_each input never reaches the chunks behind
            # end_for_each, so short-circuit straight to Summary.Done.
            await data.async_emit("Summary.Done", None)
            return []
        return candidates

    return prepare_summary_candidates


def create_summarize_candidate_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    # All candidates (primary first, then backups) flow through one for_each
    # pass. Each candidate checks the quota before doing expensive work, so
    # once enough stories are summarized the rest fall through cheaply.
    # NOTE: do not re-emit an event from its own handler chain to build a
    # dispatch/merge loop here - TriggerFlow never fires the re-emitted event
    # and the whole flow hangs.
    async def summarize_candidate(data: TriggerFlowRuntimeData) -> dict[str, Any]:
        candidate = data.value if isinstance(data.value, dict) else {}
        news = candidate.get("news")
        is_backup = bool(candidate.get("is_backup"))
        if not isinstance(news, dict):
            return {"news": {}, "is_backup": is_backup, "status": "invalid"}

        target_count = safe_int(data.state.get("summary_target_count"), 0)
        summary_results = data.state.get("summary_results") or []
        title = str(news.get("title") or "").strip()
        logger = require_logger(data)
        if len(summary_results) >= target_count:
            return {"news": {"title": title}, "is_backup": is_backup, "status": "quota_reached"}

        column_outline = _get_summary_column_outline(data)
        summarized = await summarize_single_news(
            config,
            logger,
            require_browse_tool(data),
            column_outline,
            news,
        )

        if isinstance(summarized, dict):
            summary_results = data.state.get("summary_results") or []
            if len(summary_results) < target_count:
                summary_results.append(summarized)
                data.state.set("summary_results", summary_results, emit=False)
                return {"news": {"title": title}, "is_backup": is_backup, "status": "summarized"}
            return {"news": {"title": title}, "is_backup": is_backup, "status": "quota_reached"}

        if is_backup:
            logger.info("[Backup News Skipped] %s", title)
        else:
            logger.info("[Primary News Failed, Will Try Backup] %s", title)
        return {"news": {"title": title}, "is_backup": is_backup, "status": "failed"}

    return summarize_candidate


def create_signal_summary_done_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    async def signal_summary_done(data: TriggerFlowRuntimeData):
        await data.async_emit("Summary.Done", None)

    return signal_summary_done


def create_finalize_summary_chunk(
    config: DailyNewsChunkConfig,
) -> Callable[[TriggerFlowRuntimeData], Any]:
    async def finalize_summary(data: TriggerFlowRuntimeData) -> dict[str, Any]:
        context = data.state.get("summary_context")
        if not isinstance(context, dict):
            return {
                "column_outline": {},
                "searched_news": [],
                "picked_news": [],
                "summarized_news": [],
            }

        result = copy.deepcopy(context)
        summarized_news = data.state.get("summary_results") or []
        result["summarized_news"] = summarized_news if isinstance(summarized_news, list) else []
        logger = require_logger(data)
        title = str(result.get("column_outline", {}).get("column_title") or "").strip()
        logger.info("[Summarized News Count] %s => %s", title, len(result["summarized_news"]))
        return result

    return finalize_summary


def _coerce_summary_context(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    column_outline = value.get("column_outline")
    searched_news = value.get("searched_news")
    picked_news = value.get("picked_news")
    if not isinstance(column_outline, dict) or not isinstance(searched_news, list) or not isinstance(picked_news, list):
        return None

    return {
        "column_outline": copy.deepcopy(column_outline),
        "searched_news": copy.deepcopy(searched_news),
        "picked_news": copy.deepcopy(picked_news),
    }


def _get_summary_column_outline(data: TriggerFlowRuntimeData) -> dict[str, Any]:
    context = data.state.get("summary_context")
    if isinstance(context, dict) and isinstance(context.get("column_outline"), dict):
        return context["column_outline"]
    return {}


def build_summary_candidates(
    config: DailyNewsChunkConfig,
    column_outline: dict[str, Any],
    searched_news: list[dict[str, Any]],
    picked_news: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    picked_urls = {
        str(news.get("url") or "").strip()
        for news in picked_news
        if str(news.get("url") or "").strip()
    }
    seen_urls: set[str] = set()

    for news in picked_news:
        url = str(news.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(
            {
                "news": copy.deepcopy(news),
                "is_backup": False,
            }
        )

    for news in searched_news:
        url = str(news.get("url") or "").strip()
        if not url or url in seen_urls or url in picked_urls:
            continue
        seen_urls.add(url)
        backup_news = copy.deepcopy(news)
        if not str(backup_news.get("recommend_comment") or "").strip():
            backup_news["recommend_comment"] = build_backup_recommend_comment(
                config,
                column_outline,
                backup_news,
            )
        candidates.append(
            {
                "news": backup_news,
                "is_backup": True,
            }
        )

    return candidates


async def pick_news(
    config: DailyNewsChunkConfig,
    column_outline: dict[str, Any],
    searched_news: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    # Keep the shortlist prompt small: inline article content is for the
    # summarize stage, not for picking.
    slimmed_candidates = [
        {key: value for key, value in news.items() if key != "content"}
        for news in searched_news
    ]
    pick_results = await (
        create_editor_agent(kind="column")
        .load_yaml_prompt(
            config.prompt_dir / "pick_news.yaml",
            mappings={
                "column_news": slimmed_candidates,
                "column_title": column_outline["column_title"],
                "column_requirement": column_outline["column_requirement"],
                "max_news_per_column": config.settings.workflow.max_news_per_column,
            },
        )
        .async_start(
            ensure_keys=[
                "[*].id",
                "[*].can_use",
                "[*].relevance_score",
                "[*].recommend_comment",
            ]
        )
    )

    if not isinstance(pick_results, list):
        return []

    picked_news = []
    seen_ids: set[int] = set()
    sorted_results = sorted(
        [item for item in pick_results if isinstance(item, dict)],
        key=lambda item: safe_int(item.get("relevance_score"), 0),
        reverse=True,
    )
    for item in sorted_results:
        if item.get("can_use") is not True:
            continue
        news_id = safe_int(item.get("id"), -1)
        if news_id < 0 or news_id >= len(searched_news) or news_id in seen_ids:
            continue
        seen_ids.add(news_id)
        picked_item = copy.deepcopy(searched_news[news_id])
        picked_item["recommend_comment"] = str(item.get("recommend_comment") or "").strip()
        picked_item["relevance_score"] = safe_int(item.get("relevance_score"), 0)
        picked_news.append(picked_item)
        if len(picked_news) >= config.settings.workflow.max_news_per_column:
            break
    return picked_news


async def summarize_single_news(
    config: DailyNewsChunkConfig,
    logger,
    browse_tool,
    column_outline: dict[str, Any],
    news: dict[str, Any],
) -> dict[str, Any] | None:
    from tools.dev_sources import GITHUB_REPO_URL_RE, fetch_github_repo_content

    url = str(news.get("url") or "")
    kind = str(news.get("kind") or "")
    inline_content = str(news.get("content") or "").strip()
    is_repo = not kind and GITHUB_REPO_URL_RE.match(url) is not None
    label = f" ({kind})" if kind else (" (repo)" if is_repo else "")
    logger.info("[Summarizing]%s %s", label, news["title"])

    trusted_content = bool(inline_content) or is_repo
    if inline_content:
        # Structured channels (releases, advisories, reddit self posts) ship
        # their content inline: no browsing round-trip needed.
        content = inline_content
    elif is_repo:
        # GitHub repo pages browse poorly as HTML; the README plus repo
        # metadata is far better input for a conversational introduction.
        content = await fetch_github_repo_content(
            url,
            proxy=config.settings.browse.proxy or config.settings.proxy,
            max_length=config.settings.browse.max_content_length,
        )
        brief = str(news.get("brief") or "").strip()
        if content and brief:
            # Surface trending signals (stars today, streak) to the model.
            content = f"Trending signals: {brief}\n\n{content}"
    else:
        content = await browse_tool.browse(url)
    content = str(content or "").strip()
    if len(content) < config.settings.browse.min_content_length:
        logger.info("[Summarizing] Failed - content too short")
        return None
    if not trusted_content and is_invalid_browse_content(content):
        logger.info("[Summarizing] Failed - invalid browsed content")
        return None

    prompt_by_kind = {
        "release": "summarize_release.yaml",
        "advisory": "summarize_advisory.yaml",
    }
    if kind in prompt_by_kind:
        prompt_file = prompt_by_kind[kind]
    elif is_repo:
        prompt_file = "summarize_repo.yaml"
    else:
        prompt_file = "summarize_news.yaml"
    summary_result = await (
        create_editor_agent(kind="column")
        .load_yaml_prompt(
            config.prompt_dir / prompt_file,
            mappings={
                "news_content": content,
                "news_title": news["title"],
                "column_requirement": column_outline["column_requirement"],
                "language": config.settings.workflow.output_language,
                "tone_instruction": tone_instruction(config.settings),
                "reader_context": reader_context(config.settings),
            },
        )
        .async_start(
            ensure_keys=[
                "can_summarize",
                "summary",
            ]
        )
    )

    if not isinstance(summary_result, dict):
        logger.info("[Summarizing] Failed - invalid summary output")
        return None
    if summary_result.get("can_summarize") is not True:
        logger.info("[Summarizing] Failed - model rejected content")
        return None

    summary = strip_greeting(str(summary_result.get("summary") or "").strip())
    if not summary:
        logger.info("[Summarizing] Failed - empty summary")
        return None

    summarized_news = copy.deepcopy(news)
    summarized_news["summary"] = summary
    # The raw inline content did its job; keep reports and JSON lean.
    summarized_news.pop("content", None)

    # Give published stories a picture: structured channels already carry one;
    # for everything else grab the page's og:image. Only runs for the few
    # stories that made the cut, so the extra request cost stays tiny.
    if not str(summarized_news.get("image") or "").strip():
        from tools.dev_sources import fetch_og_image

        try:
            image = await fetch_og_image(
                url,
                proxy=config.settings.browse.proxy or config.settings.proxy,
            )
        except Exception:
            image = ""
        if image:
            summarized_news["image"] = image

    logger.info("[Summarizing] Success")
    return summarized_news


def build_backup_recommend_comment(
    config: DailyNewsChunkConfig,
    column_outline: dict[str, Any],
    news: dict[str, Any],
) -> str:
    title = str(column_outline.get("column_title") or "this section")
    news_title = str(news.get("title") or "").strip()
    if is_chinese_language(config.settings.workflow.output_language):
        if news_title:
            return f"该报道与“{title}”存在明确关联，可作为备用候选：{news_title}。"
        return f"该报道与“{title}”存在明确关联，可作为备用候选。"
    if news_title:
        return f"This story is meaningfully related to {title} and is kept as a backup candidate: {news_title}."
    return f"This story is meaningfully related to {title} and is kept as a backup candidate."


__all__ = [
    "create_prepare_summary_candidates_chunk",
    "create_summarize_candidate_chunk",
    "create_signal_summary_done_chunk",
    "create_finalize_summary_chunk",
    "pick_news",
]
