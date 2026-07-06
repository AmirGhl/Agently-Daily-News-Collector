from __future__ import annotations

import re

# Small local models (qwen, llama...) love to open Persian/English summaries
# with a salutation despite instructions. Strip any leading greeting so the
# published copy always starts with substance. Lives here (not in workflow)
# so renderers and delivery can clean up old reports too.
_GREETING_WORDS = (
    r"سلام(?:\s+(?:رفیق|دوست\s+من|دوستان|همکار|بچه‌ها))?"
    r"|درود(?:\s+بر\s+شما)?"
    r"|هی|هاي|اهلا|مرحبا"
    r"|hello\s+there|hello|hi\s+there|hi|hey\s+there|hey|greetings|salam"
    r"|(?:hello|hi|hey)\s+(?:everyone|folks|friend|friends|all)"
)
_GREETING_RE = re.compile(
    rf"^\s*(?:(?:{_GREETING_WORDS})\s*[!.,،؛:\-–—]*\s*)+",
    re.IGNORECASE,
)


def strip_greeting(text: str) -> str:
    """Remove a leading greeting ('سلام! ...', 'Hey, ...') from LLM output."""
    cleaned = _GREETING_RE.sub("", text or "", count=1).lstrip()
    return cleaned if cleaned else (text or "").strip()


__all__ = ["strip_greeting"]
