from __future__ import annotations

import asyncio
import logging
import re
from html import escape
from pathlib import Path
from typing import Any

import httpx

from .config import AppSettings
from .textutils import strip_greeting

TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024

_RTL_MARKERS = ("persian", "farsi", "arabic", "hebrew", "urdu")

_KIND_EMOJI = {
    "release": "🏷",
    "advisory": "🛡",
}
_SOURCE_EMOJI = (
    ("github", "📦"),
    ("hacker news", "🔶"),
    ("reddit", "💬"),
    ("lobsters", "🦞"),
    ("dev.to", "✍️"),
    ("daily.dev", "✍️"),
    ("product hunt", "🚀"),
)

_LABELS = {
    "fa": {
        "headlines": "سرخط‌های امروز",
        "sections": "بخش",
        "stories": "مطلب",
        "why": "چرا مهم است",
        "read_more": "مشاهده کامل",
        "source": "منبع",
        "end": "پایان گزارش امروز",
        "attached": "نسخهٔ کامل HTML پیوست شد — آفلاین و قابل چاپ.",
        "of": "از",
        "action": "اقدام پیشنهادی",
    },
    "en": {
        "headlines": "Today's headlines",
        "sections": "sections",
        "stories": "stories",
        "why": "Why it matters",
        "read_more": "Read more",
        "source": "Source",
        "end": "End of today's briefing",
        "attached": "Full HTML edition attached — offline & printable.",
        "of": "of",
        "action": "Suggested action",
    },
}

_NUM_EMOJI = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")


def _labels_for(result: dict[str, Any]) -> dict[str, str]:
    language = str(result.get("language") or "").strip().lower()
    if any(marker in language for marker in _RTL_MARKERS) or language.startswith("fa"):
        return _LABELS["fa"]
    return _LABELS["en"]


def _hashtag(text: str) -> str:
    cleaned = re.sub(r"[^\w؀-ۿ]+", "_", str(text or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return f"#{cleaned}" if cleaned else ""


def _story_emoji(news: dict[str, Any]) -> str:
    kind = str(news.get("kind") or "").strip()
    if kind in _KIND_EMOJI:
        return _KIND_EMOJI[kind]
    source = str(news.get("source") or "").lower()
    url = str(news.get("url") or "").lower()
    for marker, emoji in _SOURCE_EMOJI:
        if marker in source:
            return emoji
    if re.search(r"github\.com/[^/]+/[^/]+/?$", url):
        return "📦"
    return "📰"


def _trim(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    # Break at a sentence end when one is reasonably close, else a word.
    for breaker in ("۔", "।", ".", "؟", "?", "!", "؛", ";"):
        pos = cut.rfind(breaker)
        if pos > limit * 0.6:
            return cut[: pos + 1]
    pos = cut.rfind(" ")
    if pos > limit * 0.6:
        cut = cut[:pos]
    return cut.rstrip() + "…"


def compose_delivery_message(result: dict[str, Any]) -> str:
    """Compact plain-text digest (webhook fallback / legacy)."""
    lines = [str(result.get("report_title") or "Daily News Report"), ""]

    tldr = result.get("tldr")
    if isinstance(tldr, list) and tldr:
        lines.extend(f"• {str(item).strip()}" for item in tldr if str(item or "").strip())
        lines.append("")

    for column in result.get("columns") or []:
        if not isinstance(column, dict):
            continue
        title = str(column.get("title") or "").strip()
        if title:
            lines.append(f"— {title} —")
        for news in column.get("news_list") or []:
            if not isinstance(news, dict):
                continue
            news_title = str(news.get("title") or "").strip()
            url = str(news.get("url") or "").strip()
            if news_title and url:
                lines.append(f"{news_title}\n{url}")
            elif news_title:
                lines.append(news_title)
        lines.append("")

    message = "\n".join(lines).strip()
    if len(message) > TELEGRAM_MESSAGE_LIMIT:
        message = message[: TELEGRAM_MESSAGE_LIMIT - 1].rstrip() + "…"
    return message


def compose_header_message(result: dict[str, Any]) -> str:
    """Channel-style opening post: masthead, date, numbered headlines."""
    labels = _labels_for(result)
    title = str(result.get("report_title") or "Daily News Report").strip()
    columns = [c for c in (result.get("columns") or []) if isinstance(c, dict)]
    story_count = sum(len(c.get("news_list") or []) for c in columns)
    date = str(result.get("generated_at") or "")[:10]

    parts = [f"🗞 <b>{escape(title)}</b>"]
    meta_bits = []
    if date:
        meta_bits.append(f"📅 {escape(date)}")
    if story_count:
        meta_bits.append(
            f"{story_count} {labels['stories']} · {len(columns)} {labels['sections']}"
        )
    if meta_bits:
        parts.append(" · ".join(meta_bits))

    tldr = [str(item).strip() for item in (result.get("tldr") or []) if str(item or "").strip()]
    if tldr:
        parts.append(f"\n⚡️ <b>{labels['headlines']}</b>\n")
        parts.append(
            "\n\n".join(
                f"{_NUM_EMOJI[index] if index < len(_NUM_EMOJI) else f'{index + 1}.'} {escape(item)}"
                for index, item in enumerate(tldr)
            )
        )

    tags = [_hashtag(str(result.get("topic") or ""))]
    tags = [tag for tag in tags if tag]
    if tags:
        parts.append("\n" + " ".join(tags))

    message = "\n".join(parts)
    if len(message) > TELEGRAM_MESSAGE_LIMIT:
        message = message[: TELEGRAM_MESSAGE_LIMIT - 1].rstrip() + "…"
    return message


def compose_story_message(
    news: dict[str, Any],
    *,
    column_title: str,
    position: str,
    labels: dict[str, str],
    limit: int,
) -> str:
    """One story as one channel post (used as caption when a photo exists)."""
    emoji = _story_emoji(news)
    title = str(news.get("title") or "").strip()
    url = str(news.get("url") or "").strip()
    source = str(news.get("source") or "").strip()
    date = str(news.get("date") or "").strip()[:10]

    headline = (
        f'{emoji} <b><a href="{escape(url, quote=True)}">{escape(title)}</a></b>'
        if url
        else f"{emoji} <b>{escape(title)}</b>"
    )
    header = headline
    if column_title:
        header += f"\n🗂 <i>{escape(column_title)}</i>"
        if position:
            header += f" · {escape(position)}"

    footer_bits = []
    if source:
        footer_bits.append(f"📎 {escape(source)}")
    if date:
        footer_bits.append(escape(date))
    tag = _hashtag(column_title)
    footer = " · ".join(footer_bits)
    if tag:
        footer = f"{footer}\n{tag}" if footer else tag

    comment = strip_greeting(str(news.get("recommend_comment") or "").strip())
    summary = strip_greeting(str(news.get("summary") or news.get("brief") or "").strip())
    action = str(news.get("action") or "").strip()
    action_reason = strip_greeting(str(news.get("action_reason") or "").strip())

    # Fixed parts first; summary and comment absorb whatever room remains.
    fixed_len = len(header) + len(footer) + 8  # separators
    room = max(limit - fixed_len, 0)
    body_parts: list[str] = []
    if summary and room > 60:
        comment_budget = min(len(comment) + 30, 220) if comment else 0
        summary_room = max(room - comment_budget, 80)
        body_parts.append(escape(_trim(summary, summary_room)))
        room -= len(body_parts[-1])
    if comment and room > 60:
        body_parts.append(f"💡 <i>{escape(_trim(comment, max(room - 20, 60)))}</i>")
    if action and room > 40:
        action_text = f"🎯 <b>{labels['action']}:</b> {escape(action)}"
        if action_reason:
            action_text += f" — {escape(_trim(action_reason, max(room - len(action_text), 60)))}"
        body_parts.append(action_text)

    message = header
    if body_parts:
        message += "\n\n" + "\n\n".join(body_parts)
    if footer:
        message += "\n\n" + footer
    if len(message) > limit:
        message = message[: limit - 1].rstrip() + "…"
    return message


def compose_footer_message(result: dict[str, Any]) -> str:
    labels = _labels_for(result)
    columns = [c for c in (result.get("columns") or []) if isinstance(c, dict)]
    story_count = sum(len(c.get("news_list") or []) for c in columns)
    sources = {
        str(news.get("source") or "").strip()
        for column in columns
        for news in column.get("news_list") or []
        if isinstance(news, dict) and str(news.get("source") or "").strip()
    }
    parts = [f"✅ <b>{labels['end']}</b>"]
    stat_bits = [f"{story_count} {labels['stories']}"]
    if sources:
        stat_bits.append(f"{len(sources)} {labels['source']}")
    parts.append("📊 " + " · ".join(stat_bits))
    model = str(result.get("model") or "").strip()
    if model:
        parts.append(f"🤖 <code>{escape(model)}</code>")
    return "\n".join(parts)


def compose_telegram_messages(result: dict[str, Any]) -> list[str]:
    """Digest mode: header + column blocks packed under the 4096 limit.
    Kept for send_style: digest and as the fallback path."""
    blocks: list[str] = [compose_header_message(result)]

    for column in result.get("columns") or []:
        if not isinstance(column, dict):
            continue
        lines: list[str] = []
        column_title = str(column.get("title") or "").strip()
        if column_title:
            lines.append(f"🗂 <b>{escape(column_title)}</b>")
        for news in column.get("news_list") or []:
            if not isinstance(news, dict):
                continue
            news_title = str(news.get("title") or "").strip()
            if not news_title:
                continue
            url = str(news.get("url") or "").strip()
            source = str(news.get("source") or "").strip()
            line = (
                f'• <a href="{escape(url, quote=True)}">{escape(news_title)}</a>'
                if url
                else f"• {escape(news_title)}"
            )
            if source:
                line += f" — <i>{escape(source)}</i>"
            lines.append(line)
        if lines:
            blocks.append("\n".join(lines))

    messages: list[str] = []
    current = ""
    for block in blocks:
        if len(block) > TELEGRAM_MESSAGE_LIMIT:
            block = block[: TELEGRAM_MESSAGE_LIMIT - 1].rstrip() + "…"
        if current and len(current) + 2 + len(block) > TELEGRAM_MESSAGE_LIMIT:
            messages.append(current)
            current = block
        else:
            current = f"{current}\n\n{block}" if current else block
    if current:
        messages.append(current)
    return messages


async def deliver_report(
    settings: AppSettings,
    result: dict[str, Any],
    logger: logging.Logger,
) -> list[str]:
    """Send the generated report to every enabled destination.

    Failures are logged but never abort the run: the report is already on disk.
    Returns the list of destinations that succeeded.
    """
    delivered: list[str] = []
    proxy = settings.proxy or None

    telegram = settings.delivery.telegram
    if telegram.enabled:
        if telegram.bot_token and telegram.chat_id:
            try:
                await _deliver_to_telegram(settings, result, telegram.proxy or proxy)
                delivered.append("telegram")
                logger.info("[Delivered] telegram chat %s", telegram.chat_id)
            except Exception as exc:
                logger.warning("[Telegram Delivery Failed] %s", exc)
        else:
            logger.warning(
                "[Telegram Delivery Skipped] bot_token/chat_id missing; "
                "set them in SETTINGS.yaml or the referenced environment variables."
            )

    webhook = settings.delivery.webhook
    if webhook.enabled:
        if webhook.url:
            try:
                await _deliver_to_webhook(webhook.url, result, proxy)
                delivered.append("webhook")
                logger.info("[Delivered] webhook %s", webhook.url)
            except Exception as exc:
                logger.warning("[Webhook Delivery Failed] %s", exc)
        else:
            logger.warning("[Webhook Delivery Skipped] url missing.")

    return delivered


class _TelegramClient:
    """Thin sender that retries 429s and paces posts like a human editor."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, chat_id: str):
        self._client = client
        self._base_url = base_url
        self._chat_id = chat_id

    async def _post(self, method: str, payload: dict[str, Any]) -> httpx.Response:
        payload = {"chat_id": self._chat_id, **payload}
        for attempt in range(3):
            response = await self._client.post(f"{self._base_url}/{method}", json=payload)
            if response.status_code == 429:
                try:
                    retry_after = float(
                        (response.json().get("parameters") or {}).get("retry_after", 3)
                    )
                except Exception:
                    retry_after = 3.0
                await asyncio.sleep(min(retry_after + 0.5, 30.0))
                continue
            return response
        return response

    async def send_message(self, text: str, *, preview: bool = False) -> None:
        response = await self._post(
            "sendMessage",
            {
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": not preview,
            },
        )
        response.raise_for_status()

    async def send_photo_or_message(self, photo_url: str, caption: str, fallback_text: str) -> None:
        """Try a photo post; degrade to a text post (with link preview) when
        Telegram rejects the image URL."""
        response = await self._post(
            "sendPhoto",
            {"photo": photo_url, "caption": caption, "parse_mode": "HTML"},
        )
        if response.status_code == 200:
            return
        await self.send_message(fallback_text, preview=True)


async def _deliver_to_telegram(
    settings: AppSettings,
    result: dict[str, Any],
    proxy: str | None,
) -> None:
    telegram = settings.delivery.telegram
    base_url = f"{TELEGRAM_API_BASE}/bot{telegram.bot_token}"
    async with httpx.AsyncClient(proxy=proxy, timeout=60.0) as client:
        sender = _TelegramClient(client, base_url, str(telegram.chat_id))
        try:
            if telegram.send_style == "channel":
                await _send_channel_style(sender, result, pace=telegram.message_delay)
            else:
                for text in compose_telegram_messages(result):
                    await sender.send_message(text)
        except httpx.HTTPStatusError:
            # HTML entity edge case? Fall back to the plain-text digest.
            response = await client.post(
                f"{base_url}/sendMessage",
                json={
                    "chat_id": telegram.chat_id,
                    "text": compose_delivery_message(result),
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()

        if not telegram.send_html_file:
            return
        html_path = (result.get("output_paths") or {}).get("html")
        if not html_path or not Path(html_path).exists():
            return
        labels = _labels_for(result)
        with open(html_path, "rb") as html_file:
            response = await client.post(
                f"{base_url}/sendDocument",
                data={
                    "chat_id": telegram.chat_id,
                    "caption": f"📄 {labels['attached']}",
                },
                files={"document": (Path(html_path).name, html_file, "text/html")},
            )
        response.raise_for_status()


async def _send_channel_style(
    sender: _TelegramClient,
    result: dict[str, Any],
    *,
    pace: float,
) -> None:
    """Famous-channel format: opening headlines post, then one post per story
    (photo when available), then a closing stats post."""
    labels = _labels_for(result)
    await sender.send_message(compose_header_message(result))

    for column in result.get("columns") or []:
        if not isinstance(column, dict):
            continue
        column_title = str(column.get("title") or "").strip()
        news_list = [n for n in (column.get("news_list") or []) if isinstance(n, dict)]
        for index, news in enumerate(news_list, 1):
            await asyncio.sleep(max(pace, 0.0))
            position = f"{index}/{len(news_list)}" if len(news_list) > 1 else ""
            image = str(news.get("image") or "").strip()
            if image:
                caption = compose_story_message(
                    news,
                    column_title=column_title,
                    position=position,
                    labels=labels,
                    limit=TELEGRAM_CAPTION_LIMIT,
                )
                fallback = compose_story_message(
                    news,
                    column_title=column_title,
                    position=position,
                    labels=labels,
                    limit=TELEGRAM_MESSAGE_LIMIT,
                )
                await sender.send_photo_or_message(image, caption, fallback)
            else:
                text = compose_story_message(
                    news,
                    column_title=column_title,
                    position=position,
                    labels=labels,
                    limit=TELEGRAM_MESSAGE_LIMIT,
                )
                # No image of our own: let Telegram unfurl the link preview.
                await sender.send_message(text, preview=True)

    await asyncio.sleep(max(pace, 0.0))
    await sender.send_message(compose_footer_message(result))


async def _deliver_to_webhook(
    url: str,
    result: dict[str, Any],
    proxy: str | None,
) -> None:
    payload = {
        "report_title": result.get("report_title"),
        "tldr": result.get("tldr") or [],
        "columns": result.get("columns") or [],
        "markdown": result.get("markdown"),
        "output_paths": result.get("output_paths") or {},
    }
    async with httpx.AsyncClient(proxy=proxy, timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


async def deliver_alert(
    settings: AppSettings,
    alert_data: dict[str, Any],
    channels: tuple[str, ...],
) -> None:
    """Deliver a breaking news alert via configured channels."""
    proxy = settings.proxy or None
    telegram = settings.delivery.telegram

    # Compose alert message
    story = alert_data.get("story", {})
    match = alert_data.get("match", {})
    topic = alert_data.get("topic", "")
    report_title = alert_data.get("report_title", "Breaking News")

    labels = _labels_for({"language": settings.workflow.output_language})
    story_title = str(story.get("title") or "").strip()
    story_url = str(story.get("url") or "").strip()
    source = str(story.get("source") or "").strip()
    date = str(story.get("date") or "").strip()[:10]
    keywords = match.get("keywords", [])
    cve_ids = match.get("cve_ids", [])
    severity = match.get("severity", 1)

    # Severity emoji
    severity_emoji = {5: "🔴", 4: "🟠", 3: "🟡", 2: "🟢", 1: "🔵"}.get(severity, "📍")

    # Build message
    parts = [
        f"{severity_emoji} <b>BREAKING ALERT</b>",
        f"📌 <b>{escape(story_title)}</b>",
    ]

    if cve_ids:
        parts.append(f"🛡 CVE: {', '.join(escape(c) for c in cve_ids)}")
    if keywords:
        parts.append(f"🔑 Keywords: {', '.join(escape(k) for k in keywords)}")
    if source:
        parts.append(f"📎 Source: {escape(source)}")
    if date:
        parts.append(f"📅 {escape(date)}")

    if story_url:
        parts.append(f"🔗 <a href=\"{escape(story_url, quote=True)}\">{labels['read_more']}</a>")

    message = "\n".join(parts)

    # Deliver via Telegram
    if "telegram" in channels and telegram.enabled and telegram.bot_token and telegram.chat_id:
        try:
            async with httpx.AsyncClient(proxy=telegram.proxy or proxy, timeout=30.0) as client:
                sender = _TelegramClient(client, f"{TELEGRAM_API_BASE}/bot{telegram.bot_token}", str(telegram.chat_id))
                await sender.send_message(message)
        except Exception as exc:
            logging.getLogger(__name__).warning("[Alert Telegram Failed] %s", exc)

    # Deliver via Webhook
    if "webhook" in channels:
        webhook = settings.delivery.webhook
        if webhook.enabled and webhook.url:
            try:
                payload = {
                    "alert": True,
                    "report_title": report_title,
                    "topic": topic,
                    "story": story,
                    "match": match,
                    "message": message,
                }
                async with httpx.AsyncClient(proxy=proxy, timeout=30.0) as client:
                    await client.post(webhook.url, json=payload)
            except Exception as exc:
                logging.getLogger(__name__).warning("[Alert Webhook Failed] %s", exc)

    # Web Push would be handled client-side via Service Worker
    # Server just needs to send push via Push API (not implemented here)


__all__ = [
    "compose_delivery_message",
    "compose_header_message",
    "compose_story_message",
    "compose_footer_message",
    "compose_telegram_messages",
    "deliver_report",
    "deliver_alert",
]
