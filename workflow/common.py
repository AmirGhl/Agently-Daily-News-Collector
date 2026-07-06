from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agently import Agently, TriggerFlowRuntimeData

from news_collector.config import AppSettings
from news_collector.history import NewsHistory
from tools.base import BrowseToolProtocol, SearchToolProtocol


@dataclass(frozen=True, slots=True)
class DailyNewsChunkConfig:
    settings: AppSettings
    prompt_dir: Path
    output_dir: Path
    model_label: str
    history: NewsHistory | None = None


def create_editor_agent(*, kind: str):
    agent = Agently.create_agent(name=f"{kind}_editor")
    if kind == "chief":
        agent.set_agent_prompt(
            "system",
            "You are a veteran newsroom chief editor who designs reliable daily news briefings.",
        )
        agent.set_agent_prompt(
            "instruct",
            [
                "Prefer recent, factual, non-duplicated stories.",
                "Keep structures stable and concise.",
            ],
        )
    else:
        agent.set_agent_prompt(
            "system",
            "You are a meticulous news editor who selects and rewrites high-signal stories.",
        )
        agent.set_agent_prompt(
            "instruct",
            [
                "Reject irrelevant or thin content.",
                "Keep comments practical and publication-ready.",
            ],
        )
    return agent


def is_chinese_language(language: str) -> bool:
    normalized = language.lower()
    return "chinese" in normalized or normalized.startswith("zh")


def tone_instruction(settings: AppSettings) -> str:
    if settings.workflow.tone == "conversational":
        return (
            "Write like a friendly senior developer chatting with a colleague: "
            "warm, direct, plain language, address the reader as 'you', "
            "and absolutely no corporate press-release phrasing. "
            "NEVER open with a greeting or salutation of any kind "
            "(no 'Hello', 'Hi', 'Hey', 'سلام', 'درود', 'خب') — start "
            "mid-conversation, directly with the first concrete fact."
        )
    return (
        "Keep a concise, professional news-brief tone. "
        "Never open with a greeting or preamble; start with the substance."
    )


# Canonical implementation lives in news_collector.textutils so the
# renderers and Telegram delivery can clean historical reports too.
from news_collector.textutils import strip_greeting  # noqa: E402  (re-export)


def reader_context(settings: AppSettings) -> str:
    stack = settings.dev_pulse.stack
    if not stack:
        return "No specific reader profile."
    return (
        f"The reader's main stack: {', '.join(stack)}. "
        "When an item genuinely connects to that stack, add one sentence on "
        "what it means for them - never force a connection that is not there."
    )


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-_")
    return cleaned or "daily-news-report"


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def require_logger(data: TriggerFlowRuntimeData) -> logging.Logger:
    return cast(logging.Logger, data.require_resource("logger"))


def require_search_tool(data: TriggerFlowRuntimeData) -> SearchToolProtocol:
    return cast(SearchToolProtocol, data.require_resource("search_tool"))


def require_browse_tool(data: TriggerFlowRuntimeData) -> BrowseToolProtocol:
    return cast(BrowseToolProtocol, data.require_resource("browse_tool"))


def require_rss_tool(data: TriggerFlowRuntimeData) -> "RssFeedTool":
    from tools.rss import RssFeedTool

    return cast(RssFeedTool, data.require_resource("rss_tool"))


def require_dev_sources_tool(data: TriggerFlowRuntimeData) -> "DevSourcesTool":
    from tools.dev_sources import DevSourcesTool

    return cast(DevSourcesTool, data.require_resource("dev_sources_tool"))


__all__ = [
    "DailyNewsChunkConfig",
    "create_editor_agent",
    "is_chinese_language",
    "strip_greeting",
    "tone_instruction",
    "reader_context",
    "safe_filename",
    "safe_int",
    "require_logger",
    "require_search_tool",
    "require_browse_tool",
    "require_rss_tool",
    "require_dev_sources_tool",
]
