from __future__ import annotations

INVALID_CONTENT_MARKERS = (
    "can not browse '",
    "fallback failed:",
    "content_empty_or_too_short",
    "we've detected unusual activity",
    "not a robot",
    "captcha",
    "access denied",
    "subscribe now",
    "enable javascript",
    "browser is out of date",
)


def is_invalid_browse_content(content: str) -> bool:
    lowered = content.strip().lower()
    return any(marker in lowered for marker in INVALID_CONTENT_MARKERS)


__all__ = ["INVALID_CONTENT_MARKERS", "is_invalid_browse_content"]
