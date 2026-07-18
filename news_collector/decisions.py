from __future__ import annotations

from copy import deepcopy
from typing import Any


_ACTIONS = {
    "act now": "ACT NOW",
    "act_now": "ACT NOW",
    "upgrade now": "ACT NOW",
    "plan": "PLAN",
    "explore": "EXPLORE",
    "monitor": "MONITOR",
    "ignore": "IGNORE",
}
_URGENCIES = {"high", "medium", "low"}


def enrich_story_actions(
    stories: list[dict[str, Any]], *, language: str
) -> list[dict[str, Any]]:
    """Return stories with a safe, display-ready editorial decision.

    Editorial model output wins when it uses a supported decision.  A small,
    deterministic fallback keeps older reports and failed model calls useful.
    """
    return [_enrich_story_action(story, language=language) for story in stories]


def enrich_columns_actions(
    columns: list[dict[str, Any]], *, language: str
) -> list[dict[str, Any]]:
    """Add decisions to every story while preserving report and column data."""
    enriched_columns: list[dict[str, Any]] = []
    for column in columns:
        copy = deepcopy(column)
        stories = copy.get("news_list")
        if isinstance(stories, list):
            copy["news_list"] = enrich_story_actions(
                [story for story in stories if isinstance(story, dict)], language=language
            )
        enriched_columns.append(copy)
    return enriched_columns


def _enrich_story_action(story: dict[str, Any], *, language: str) -> dict[str, Any]:
    enriched = deepcopy(story)
    action = _normalize_action(enriched.get("action"))
    urgency = _normalize_urgency(enriched.get("urgency"))
    if action is None:
        action, urgency = _fallback_decision(enriched)
    enriched["action"] = action
    enriched["urgency"] = urgency or "low"
    reason = str(enriched.get("action_reason") or "").strip()
    enriched["action_reason"] = reason or _fallback_reason(action, language)
    return enriched


def _normalize_action(value: object) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", " ")
    return _ACTIONS.get(normalized)


def _normalize_urgency(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _URGENCIES else None


def _fallback_decision(story: dict[str, Any]) -> tuple[str, str]:
    kind = str(story.get("kind") or "").strip().lower()
    if kind == "advisory":
        return "ACT NOW", "high"
    if kind == "release":
        return "PLAN", "medium"
    return "EXPLORE", "low"


def _fallback_reason(action: str, language: str) -> str:
    if language.strip().lower().startswith(("fa", "persian", "farsi")):
        return {
            "ACT NOW": "منبع را بررسی کنید و اثر آن بر کار فعلی‌تان را بسنجید.",
            "PLAN": "تغییرات را برای چرخهٔ بعدی بررسی و زمان‌بندی کنید.",
            "EXPLORE": "اگر با کار شما مرتبط است، منبع را برای بررسی بیشتر باز کنید.",
            "MONITOR": "این مورد را زیر نظر بگیرید تا اطلاعات بیشتری منتشر شود.",
            "IGNORE": "فعلاً اقدام مشخصی برای این مورد لازم نیست.",
        }[action]
    return {
        "ACT NOW": "Review the source and assess its impact on your current work.",
        "PLAN": "Review the changes and schedule them for a future work cycle.",
        "EXPLORE": "Open the source if it is relevant to work you are doing.",
        "MONITOR": "Keep an eye on this item as more information emerges.",
        "IGNORE": "No specific action is needed for this item right now.",
    }[action]


__all__ = ["enrich_columns_actions", "enrich_story_actions"]
