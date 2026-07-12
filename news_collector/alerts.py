from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .config import AppSettings


# Default high-severity keywords that trigger breaking alerts
DEFAULT_BREAKING_KEYWORDS = (
    # Security
    "cve", "vulnerability", "exploit", "zero-day", "zeroday",
    "security advisory", "security update", "patch", "hotfix",
    "rce", "remote code execution", "privilege escalation",
    "authentication bypass", "sql injection", "xss",
    # Outages/Incidents
    "outage", "incident", "downtime", "service disruption",
    "postmortem", "root cause", "degraded performance",
    "api down", "platform down", "service unavailable",
    # Critical releases
    "critical release", "emergency release", "security release",
    "breaking change", "migration required", "upgrade required",
    # Supply chain
    "supply chain", "malicious package", "typosquatting",
    "dependency confusion", "compromised",
)

# Allow-list domains that are trusted sources for alerts
DEFAULT_ALLOWLIST_DOMAINS = (
    "github.com", "gitlab.com", "bitbucket.org",
    "hackernews.com", "ycombinator.com",
    "theregister.com", "arstechnica.com", "theverge.com",
    "cloudflare.com", "google.com", "microsoft.com", "amazon.com",
    "aws.amazon.com", "status.github.com", "status.gitlab.com",
    "status.cloudflare.com", "status.aws.amazon.com",
)

# Regex for CVE IDs
CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)

# Regex for version numbers that might indicate critical releases
VERSION_PATTERN = re.compile(r"\b(v?\d+\.\d+\.\d+(?:[-.]\w+)?)\b")


@dataclass
class AlertConfig:
    """Configuration for breaking news alerts."""
    enabled: bool = True
    keywords: tuple[str, ...] = DEFAULT_BREAKING_KEYWORDS
    allowlist_domains: tuple[str, ...] = DEFAULT_ALLOWLIST_DOMAINS
    severity_threshold: int = 1  # 1=any match, 2=multiple matches or CVE
    cooldown_minutes: int = 30  # Minimum time between alerts for same topic
    channels: tuple[str, ...] = ("telegram", "webhook", "webpush")  # Delivery channels


@dataclass
class AlertMatch:
    """Result of alert detection."""
    matched: bool
    matched_keywords: list[str]
    cve_ids: list[str]
    severity: int  # 1-5
    source_domain: str


class AlertEngine:
    """Detects breaking news stories based on configurable rules."""

    def __init__(self, config: AlertConfig | None = None):
        self.config = config or AlertConfig()
        self._keyword_regex = self._compile_keywords()
        self._recent_alerts: dict[str, float] = {}  # topic_hash -> timestamp

    def _compile_keywords(self) -> re.Pattern:
        """Compile keywords into a single regex for fast matching."""
        # Escape special regex chars and join with OR
        escaped = [re.escape(kw) for kw in self.config.keywords]
        pattern = r"(?i)(" + "|".join(escaped) + r")"
        return re.compile(pattern)

    def check_story(self, story: dict[str, Any]) -> AlertMatch:
        """Check if a story matches breaking news criteria."""
        title = str(story.get("title") or "").strip()
        summary = str(story.get("summary") or story.get("brief") or "").strip()
        source = str(story.get("source") or "").strip().lower()
        url = str(story.get("url") or "").strip().lower()

        # Extract domain from URL
        source_domain = ""
        if url:
            try:
                from urllib.parse import urlparse
                source_domain = urlparse(url).netloc.lower().replace("www.", "")
            except Exception:
                pass

        # Combine text for matching
        text = f"{title} {summary}"

        # Check for CVE IDs
        cve_ids = CVE_PATTERN.findall(text)

        # Check keywords
        keyword_matches = self._keyword_regex.findall(text)

        # Calculate severity
        severity = 0
        if cve_ids:
            severity = max(severity, 5)  # CVE = highest
        if keyword_matches:
            severity = max(severity, len(keyword_matches) + 1)

        # Check allowlist
        is_allowlisted = any(d in source_domain for d in self.config.allowlist_domains)

        # Determine if alert should fire
        matched = (
            severity >= self.config.severity_threshold
            and (is_allowlisted or severity >= 3)  # Non-allowlisted needs higher severity
        )

        return AlertMatch(
            matched=matched,
            matched_keywords=list(set(keyword_matches)),
            cve_ids=list(set(cve_ids)),
            severity=severity,
            source_domain=source_domain,
        )

    def should_alert(self, story: dict[str, Any], topic: str) -> tuple[bool, AlertMatch]:
        """Check if alert should fire, considering cooldown."""
        match = self.check_story(story)
        if not match.matched:
            return False, match

        # Cooldown check
        import time
        topic_hash = f"{topic}:{story.get('url', '')}"
        now = time.time()
        last_alert = self._recent_alerts.get(topic_hash, 0)
        if now - last_alert < self.config.cooldown_minutes * 60:
            return False, match  # In cooldown

        self._recent_alerts[topic_hash] = now
        return True, match


def build_alert_config(settings: AppSettings) -> AlertConfig:
    """Build AlertConfig from settings."""
    # Read from settings if available, otherwise use defaults
    alerts_block = getattr(settings, "alerts", None)
    if alerts_block is None:
        # Try to get from raw settings dict
        alerts_block = getattr(settings, "_raw_alerts_block", {})

    if isinstance(alerts_block, dict):
        keywords = tuple(alerts_block.get("keywords", DEFAULT_BREAKING_KEYWORDS))
        allowlist = tuple(alerts_block.get("allowlist_domains", DEFAULT_ALLOWLIST_DOMAINS))
        severity = int(alerts_block.get("severity_threshold", 1))
        cooldown = int(alerts_block.get("cooldown_minutes", 30))
        channels = tuple(alerts_block.get("channels", ("telegram", "webhook", "webpush")))
        enabled = bool(alerts_block.get("enabled", True))
    else:
        keywords = DEFAULT_BREAKING_KEYWORDS
        allowlist = DEFAULT_ALLOWLIST_DOMAINS
        severity = 1
        cooldown = 30
        channels = ("telegram", "webhook", "webpush")
        enabled = True

    return AlertConfig(
        enabled=enabled,
        keywords=keywords,
        allowlist_domains=allowlist,
        severity_threshold=severity,
        cooldown_minutes=cooldown,
        channels=channels,
    )


__all__ = [
    "AlertConfig",
    "AlertMatch",
    "AlertEngine",
    "build_alert_config",
    "DEFAULT_BREAKING_KEYWORDS",
    "DEFAULT_ALLOWLIST_DOMAINS",
    "CVE_PATTERN",
]