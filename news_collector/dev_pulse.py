from __future__ import annotations

from .config import AppSettings

DEV_PULSE_TOPIC = "Developer Pulse"

# Fixed outline: dev-pulse columns read from structured channels
# (see tools/dev_sources.py) instead of web-search keywords.
DEV_PULSE_OUTLINE = {
    "report_title": "Developer Pulse — Today in Code",
    "column_list": [
        {
            "column_title": "Trending Repositories",
            "column_requirement": (
                "GitHub repositories that are trending right now, gaining stars "
                "unusually fast in the last 24-48 hours, or brand-new projects "
                "taking off. Prefer practical developer tools, frameworks, and "
                "interesting engineering over awareness lists and pure content "
                "collections."
            ),
            "source_channels": ["github_trending", "github_rising", "github_new"],
        },
        {
            "column_title": "Fresh Releases",
            "column_requirement": (
                "New releases of the projects the reader follows. Focus on what "
                "changed, whether anything breaks, and whether upgrading now is "
                "worth it."
            ),
            "source_channels": ["github_releases"],
        },
        {
            "column_title": "Security Watch",
            "column_requirement": (
                "Fresh high-severity security advisories in the reader's package "
                "ecosystems. Focus on affected versions, real-world impact, and "
                "the concrete fix."
            ),
            "source_channels": ["github_advisories"],
        },
        {
            "column_title": "Hot Developer News",
            "column_requirement": (
                "The biggest programming and technology stories developers are "
                "discussing today: releases, languages, infrastructure, AI dev "
                "tools, security incidents, and notable engineering write-ups."
            ),
            "source_channels": ["hackernews"],
        },
        {
            "column_title": "Product Radar",
            "column_requirement": (
                "New product launches a developer would actually care about: "
                "developer tools, APIs, AI/agent products, infrastructure, and "
                "open-source launches from today's Product Hunt front page. "
                "Skip purely consumer apps with no engineering angle."
            ),
            "source_channels": ["product_hunt"],
        },
        {
            "column_title": "Community Buzz",
            "column_requirement": (
                "What the developer community itself is talking about: highly "
                "upvoted discussions, hands-on experiences, hot takes, and "
                "practical threads worth a developer's attention."
            ),
            "source_channels": ["reddit", "lobsters", "devto", "daily_dev"],
        },
    ],
}


def build_dev_pulse_columns(settings: AppSettings) -> list[dict]:
    """Outline columns, dropping the ones whose sources are unconfigured."""
    columns = []
    for column in DEV_PULSE_OUTLINE["column_list"]:
        channels = column["source_channels"]
        if channels == ["github_releases"] and not settings.dev_pulse.watch_repos:
            continue
        if channels == ["github_advisories"] and not settings.dev_pulse.security_ecosystems:
            continue
        column = dict(column)
        # User-configured feeds (X bridges, blogs, …) join the community column.
        if "reddit" in channels and settings.dev_pulse.extra_feeds:
            column["source_channels"] = [*channels, "extra_feeds"]
        columns.append(column)
    return columns


def apply_dev_pulse(settings: AppSettings) -> None:
    """Switch loaded settings into dev-pulse mode."""
    columns = build_dev_pulse_columns(settings)
    settings.outline.use_customized = True
    settings.outline.customized = {
        "report_title": DEV_PULSE_OUTLINE["report_title"],
        "column_list": columns,
    }
    settings.workflow.max_column_num = max(
        settings.workflow.max_column_num,
        len(columns),
    )
    settings.workflow.tone = "conversational"


__all__ = ["DEV_PULSE_TOPIC", "DEV_PULSE_OUTLINE", "apply_dev_pulse"]
