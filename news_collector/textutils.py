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

_RLM = "\u200f"  # Right-to-Left Mark
_LRM = "\u200e"  # Left-to-Right Mark
_RTL_LANG_PREFIXES = ("fa", "ar", "he", "ur")


def strip_greeting(text: str) -> str:
    """Remove a leading greeting ('سلام! ...', 'Hey, ...') from LLM output."""
    cleaned = _GREETING_RE.sub("", text or "", count=1).lstrip()
    return cleaned if cleaned else (text or "").strip()


def is_rtl_language(language: str) -> bool:
    """Detect if the output language is RTL (Persian, Arabic, Hebrew, Urdu)."""
    normalized = language.strip().lower()
    markers = ("persian", "farsi", "arabic", "hebrew", "urdu")
    return any(m in normalized for m in markers) or normalized.startswith(_RTL_LANG_PREFIXES)


def wrap_mixed(text: str, language: str) -> str:
    """Wrap text with the appropriate Unicode bidi mark for mixed RTL/LTR.

    When the target language is RTL (Persian/Arabic) and the text contains
    both RTL and LTR characters, prepend an RLM so punctuation and isolated
    English words flow correctly within the Persian sentence.
    """
    if not text or not is_rtl_language(language):
        return text
    has_rtl = bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u0590-\u05FF\u0700-\u074F]", text))
    has_ltr = bool(re.search(r"[a-zA-Z0-9]", text))
    if has_rtl and has_ltr:
        return f"{_RLM}{text}"
    return text


def ensure_markdown_rtl(text: str, language: str) -> str:
    """Ensure RTL text renders correctly in markdown by adding RLM markers.

    For Persian/Arabic markdown output, this wraps mixed-content lines so
    that the English segments and punctuation appear in the correct visual
    order when viewed in a terminal or markdown renderer.
    """
    if not text or not is_rtl_language(language):
        return text
    lines = text.split("\n")
    fixed = []
    for line in lines:
        has_rtl = bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u0590-\u05FF\u0700-\u074F]", line))
        has_ltr = bool(re.search(r"[a-zA-Z0-9]", line))
        if has_rtl and has_ltr:
            fixed.append(f"{_RLM}{line}")
        else:
            fixed.append(line)
    return "\n".join(fixed)


__all__ = ["strip_greeting", "is_rtl_language", "wrap_mixed", "ensure_markdown_rtl"]
