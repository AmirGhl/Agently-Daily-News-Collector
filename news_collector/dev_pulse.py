from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .config import AppSettings

DEV_PULSE_TOPIC = "Developer Pulse"

DEV_PULSE_SECTIONS = {
    "trending": {
        "column_title": "Trending Repositories",
        "column_requirement": (
            "Hot GitHub repos that exploded overnight — rockets strapped to "
            "new stars, forks flying, issue trackers on fire. Scoop up the "
            "practical tools, the clever frameworks, and the sheer engineering "
            "audacity before the rest of the internet wakes up."
        ),
        "source_channels": ["github_trending", "github_rising", "github_new"],
        "description": "GitHub trending, rising & new repos — hottest projects right now",
    },
    "releases": {
        "column_title": "Fresh Releases",
        "column_requirement": (
            "The projects the reader follows just cut a new version. "
            "Ship or skip? Break down what changed, what breaks, and whether "
            "upgrading tonight keeps you ahead — or in the hot seat tomorrow."
        ),
        "source_channels": ["github_releases"],
        "description": "New releases from repos you watch — automated changelog summaries",
    },
    "security": {
        "column_title": "Security Watch",
        "column_requirement": (
            "CVEs that dropped in the last hours — the ones your "
            "package.json, requirements.txt, or Cargo.toml care about. Cut "
            "through the noise: affected versions, real-world blast radius, "
            "and the exact patch that makes it stop hurting."
        ),
        "source_channels": ["github_advisories"],
        "description": "GitHub security advisories — filtered by your ecosystems (pip/npm/go/rust/maven)",
    },
    "hot_news": {
        "column_title": "Hot Developer News",
        "column_requirement": (
            "The stories that every developer group chat is linking right now: "
            "a surprise framework release, a language milestone, an outage "
            "that reshuffled the internet, an AI coding demo that broke "
            "Twitter, or an engineering post-mortem so good it should be "
            "required reading."
        ),
        "source_channels": ["hackernews"],
        "description": "Top stories from Hacker News — tech news that developers actually read",
    },
    "products": {
        "column_title": "Product Radar",
        "column_requirement": (
            "Today's Product Hunt front page — but through a developer lens. "
            "New APIs, CLI tools, AI/agent infrastructure, databases, and "
            "the open-source launches that the tech Twitterati are actually "
            "deploying. Consumer fluff gets left on the cutting-room floor."
        ),
        "source_channels": ["product_hunt"],
        "description": "Developer-relevant launches from Product Hunt — APIs, CLIs, infra tools",
    },
    "community": {
        "column_title": "Community Buzz",
        "column_requirement": (
            "The raw developer hive mind: Reddit threads with 500+ upvotes "
            "that turned into holy wars and then into wisdom, Lobsters deep-"
            "dives, dev.to hot takes that aged well, and daily.dev stories "
            "the algorithm got right for once."
        ),
        "source_channels": ["reddit", "lobsters", "devto", "daily_dev"],
        "description": "Reddit, Lobsters, dev.to, daily.dev — developer discussions & hot takes",
    },
}


# Velocity thresholds for badges
VELOCITY_THRESHOLDS = {
    "rocket": 100,      # stars/hour > 100
    "trending": 50,     # points/hour > 50
    "hot": 20,          # velocity > 20
}


def calculate_velocity(news: dict[str, Any]) -> dict[str, Any]:
    """Calculate trend velocity metrics for a story."""
    source = str(news.get("source") or "").lower()
    url = str(news.get("url") or "").lower()

    velocity_data = {
        "score": 0,
        "unit": "",
        "badge": "",
        "emoji": "",
    }

    # GitHub repos - stars per hour
    if "github" in source or "github.com" in url:
        stars = int(news.get("stars") or news.get("stargazers_count") or 0)
        created_at = news.get("created_at") or news.get("pushed_at")
        if created_at and stars > 0:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                hours = max(1, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
                stars_per_hour = stars / hours
                velocity_data["score"] = round(stars_per_hour, 1)
                velocity_data["unit"] = "⭐/hr"
                if stars_per_hour >= VELOCITY_THRESHOLDS["rocket"]:
                    velocity_data["badge"] = "rocket"
                    velocity_data["emoji"] = "🚀"
                elif stars_per_hour >= VELOCITY_THRESHOLDS["trending"]:
                    velocity_data["badge"] = "trending"
                    velocity_data["emoji"] = "📈"
                elif stars_per_hour >= VELOCITY_THRESHOLDS["hot"]:
                    velocity_data["badge"] = "hot"
                    velocity_data["emoji"] = "🔥"
            except Exception:
                pass

    # Hacker News - points per hour
    elif "hackernews" in source or "ycombinator" in source:
        points = int(news.get("points") or news.get("score") or 0)
        created_at = news.get("created_at") or news.get("time")
        if created_at and points > 0:
            try:
                dt = datetime.fromtimestamp(int(created_at), tz=timezone.utc)
                hours = max(1, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
                points_per_hour = points / hours
                velocity_data["score"] = round(points_per_hour, 1)
                velocity_data["unit"] = "pts/hr"
                if points_per_hour >= VELOCITY_THRESHOLDS["rocket"]:
                    velocity_data["badge"] = "rocket"
                    velocity_data["emoji"] = "🚀"
                elif points_per_hour >= VELOCITY_THRESHOLDS["trending"]:
                    velocity_data["badge"] = "trending"
                    velocity_data["emoji"] = "📈"
                elif points_per_hour >= VELOCITY_THRESHOLDS["hot"]:
                    velocity_data["badge"] = "hot"
                    velocity_data["emoji"] = "🔥"
            except Exception:
                pass

    # Reddit - upvotes per hour
    elif "reddit" in source:
        score = int(news.get("score") or news.get("ups") or 0)
        created_at = news.get("created_at") or news.get("created_utc")
        if created_at and score > 0:
            try:
                dt = datetime.fromtimestamp(int(created_at), tz=timezone.utc)
                hours = max(1, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
                upvotes_per_hour = score / hours
                velocity_data["score"] = round(upvotes_per_hour, 1)
                velocity_data["unit"] = "⬆/hr"
                if upvotes_per_hour >= VELOCITY_THRESHOLDS["rocket"]:
                    velocity_data["badge"] = "rocket"
                    velocity_data["emoji"] = "🚀"
                elif upvotes_per_hour >= VELOCITY_THRESHOLDS["trending"]:
                    velocity_data["badge"] = "trending"
                    velocity_data["emoji"] = "📈"
                elif upvotes_per_hour >= VELOCITY_THRESHOLDS["hot"]:
                    velocity_data["badge"] = "hot"
                    velocity_data["emoji"] = "🔥"
            except Exception:
                pass

    # Lobsters, dev.to, daily.dev - similar velocity
    elif any(s in source for s in ("lobsters", "dev.to", "daily.dev")):
        score = int(news.get("score") or news.get("upvotes") or news.get("reactions") or 0)
        created_at = news.get("created_at") or news.get("published_at")
        if created_at and score > 0:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                hours = max(1, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)
                velocity_data["score"] = round(score / hours, 1)
                velocity_data["unit"] = "/hr"
                if velocity_data["score"] >= VELOCITY_THRESHOLDS["rocket"]:
                    velocity_data["badge"] = "rocket"
                    velocity_data["emoji"] = "🚀"
                elif velocity_data["score"] >= VELOCITY_THRESHOLDS["trending"]:
                    velocity_data["badge"] = "trending"
                    velocity_data["emoji"] = "📈"
                elif velocity_data["score"] >= VELOCITY_THRESHOLDS["hot"]:
                    velocity_data["badge"] = "hot"
                    velocity_data["emoji"] = "🔥"
            except Exception:
                pass

    return velocity_data


def enrich_with_velocity(news_list: list[dict]) -> list[dict]:
    """Add velocity data to each story in the list."""
    for news in news_list:
        if isinstance(news, dict):
            news["velocity"] = calculate_velocity(news)
    return news_list


def build_dev_pulse_title() -> str:
    """Generate a unique daily title for Developer Pulse."""
    today = datetime.now()
    date_en = today.strftime("%B %d, %Y")
    date_fa_map = {
        1: "ژانویه", 2: "فوریه", 3: "مارس", 4: "آوریل", 5: "مه", 6: "ژوئن",
        7: "ژوئیه", 8: "اوت", 9: "سپتامبر", 10: "اکتبر", 11: "نوامبر", 12: "دسامبر",
    }
    fa_month = date_fa_map[today.month]
    return f"Developer Pulse — {date_en}"


def build_dev_pulse_columns(settings: AppSettings) -> list[dict]:
    """Build active columns from enabled sections."""
    enabled = settings.dev_pulse.enabled_sections
    columns = []
    for section_id in DEV_PULSE_SECTIONS:
        if enabled and section_id not in enabled:
            continue
        section = DEV_PULSE_SECTIONS[section_id]
        channels = section["source_channels"]
        if channels == ["github_releases"] and not settings.dev_pulse.watch_repos:
            continue
        if channels == ["github_advisories"] and not settings.dev_pulse.security_ecosystems:
            continue
        column = dict(section)
        # Extra feeds join the community column
        if "reddit" in channels and settings.dev_pulse.extra_feeds:
            column["source_channels"] = [*channels, "extra_feeds"]
        columns.append(column)
    return columns


def apply_dev_pulse(settings: AppSettings) -> None:
    """Switch loaded settings into dev-pulse mode."""
    columns = build_dev_pulse_columns(settings)
    settings.outline.use_customized = True
    settings.outline.customized = {
        "report_title": build_dev_pulse_title(),
        "column_list": columns,
    }
    settings.workflow.max_column_num = max(
        settings.workflow.max_column_num,
        len(columns),
    )
    settings.workflow.tone = "conversational"


__all__ = [
    "DEV_PULSE_TOPIC",
    "DEV_PULSE_SECTIONS",
    "VELOCITY_THRESHOLDS",
    "calculate_velocity",
    "enrich_with_velocity",
    "build_dev_pulse_title",
    "build_dev_pulse_columns",
    "apply_dev_pulse",
]
