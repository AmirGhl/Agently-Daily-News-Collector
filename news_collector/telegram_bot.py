"""Two-way Telegram bot: message the bot, get a briefing back.

Long-polls getUpdates and answers /news, /dev and /weekly commands sent from
the configured chat only (DELIVERY.telegram.chat_id). Every other sender is
ignored silently, so exposing the bot publicly never burns API credit.

Run with:  python app.py --bot   (or DailyNewsCollector.exe --bot)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from .config import AppSettings
from .delivery import TELEGRAM_API_BASE, deliver_report

HELP_TEXT = (
    "🗞 Daily News Collector\n\n"
    "/news <topic> — generate a briefing about <topic>\n"
    "/dev — developer pulse briefing\n"
    "/weekly — digest of the last 7 days\n"
    "/help — this message\n\n"
    "Generation takes a few minutes; the report arrives right here."
)


class TelegramBot:
    def __init__(
        self,
        *,
        settings_path: Path,
        root_dir: Path,
        logger: logging.Logger,
    ):
        self.settings_path = settings_path
        self.root_dir = root_dir
        self.logger = logger
        settings = AppSettings.load(settings_path)
        telegram = settings.delivery.telegram
        if not telegram.bot_token or not telegram.chat_id:
            raise EnvironmentError(
                "The bot needs DELIVERY.telegram.bot_token and chat_id - "
                "set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env."
            )
        self.allowed_chat_id = str(telegram.chat_id)
        self.proxy = telegram.proxy or settings.proxy or None
        self.base_url = f"{TELEGRAM_API_BASE}/bot{telegram.bot_token}"
        self.busy = False

    async def run(self) -> None:
        self.logger.info(
            "[Bot] listening for /news, /dev and /weekly from chat %s",
            self.allowed_chat_id,
        )
        async with httpx.AsyncClient(timeout=65, proxy=self.proxy) as client:
            offset = await self._skip_backlog(client)
            while True:
                params: dict[str, Any] = {"timeout": 50}
                if offset is not None:
                    params["offset"] = offset
                try:
                    response = await client.get(f"{self.base_url}/getUpdates", params=params)
                    payload = response.json()
                except Exception as exc:
                    self.logger.warning("[Bot] poll failed: %s", exc)
                    await asyncio.sleep(5)
                    continue
                for update in payload.get("result", []):
                    offset = int(update.get("update_id", 0)) + 1
                    await self._handle(client, update)

    async def _skip_backlog(self, client: httpx.AsyncClient) -> int | None:
        """Commands sent while the bot was offline should not fire on startup."""
        try:
            response = await client.get(
                f"{self.base_url}/getUpdates", params={"offset": -1, "timeout": 0}
            )
            updates = response.json().get("result", [])
        except Exception:
            return None
        if updates:
            return int(updates[-1].get("update_id", 0)) + 1
        return None

    async def _handle(self, client: httpx.AsyncClient, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("channel_post") or {}
        chat_id = str((message.get("chat") or {}).get("id") or "")
        text = str(message.get("text") or "").strip()
        if not text or chat_id != self.allowed_chat_id:
            return
        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0].lower()
        topic = argument.strip()

        if command in ("/start", "/help"):
            await self._send(client, HELP_TEXT)
            return
        if command not in ("/news", "/dev", "/weekly"):
            await self._send(client, "Unknown command — try /help.")
            return
        if command == "/news" and not topic:
            await self._send(client, "Usage: /news <topic>")
            return
        if self.busy:
            await self._send(
                client,
                "⏳ Still working on the previous briefing — try again in a few minutes.",
            )
            return

        label = {
            "/news": f"“{topic}”",
            "/dev": "developer pulse",
            "/weekly": "weekly digest",
        }[command]
        self.busy = True
        await self._send(client, f"🛠 Generating {label} — this takes a few minutes…")
        try:
            result, settings = await asyncio.to_thread(self._generate, command, topic)
            if result is None:
                await self._send(client, "Nothing to digest from the last 7 days.")
                return
            delivered = await deliver_report(settings, result, self.logger)
            if "telegram" not in delivered:
                await self._send(
                    client,
                    "⚠️ The report was generated but delivery failed — check the logs.",
                )
        except Exception as exc:
            self.logger.exception("[Bot] generation failed: %s", exc)
            await self._send(client, f"❌ Failed: {exc}")
        finally:
            self.busy = False

    def _generate(
        self, command: str, topic: str
    ) -> tuple[dict[str, Any] | None, AppSettings]:
        """Runs in a worker thread; the polling loop stays responsive."""
        settings = AppSettings.load(self.settings_path)
        # The reply always goes back through Telegram, whatever the YAML says.
        settings.delivery.telegram.enabled = True
        settings.delivery.webhook.enabled = False

        if command == "/weekly":
            from .collector import DailyNewsCollector
            from .weekly import generate_weekly_digest

            collector = DailyNewsCollector(
                settings=settings, root_dir=self.root_dir, logger=self.logger
            )
            result = asyncio.run(
                generate_weekly_digest(
                    settings=settings,
                    root_dir=self.root_dir,
                    logger=self.logger,
                    model_label=collector.model_label,
                )
            )
            return result, settings

        if command == "/dev":
            from .dev_pulse import DEV_PULSE_TOPIC, apply_dev_pulse

            apply_dev_pulse(settings)
            topic = topic or DEV_PULSE_TOPIC

        from .collector import run_with_model_fallback

        result = run_with_model_fallback(
            settings=settings,
            root_dir=self.root_dir,
            logger=self.logger,
            topic=topic,
        )
        return result, settings

    async def _send(self, client: httpx.AsyncClient, text: str) -> None:
        try:
            await client.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.allowed_chat_id, "text": text},
            )
        except Exception as exc:
            self.logger.warning("[Bot] send failed: %s", exc)


def run_bot(*, settings_path: Path, root_dir: Path, logger: logging.Logger) -> int:
    bot = TelegramBot(settings_path=settings_path, root_dir=root_dir, logger=logger)
    print(f"Telegram bot is listening (chat {bot.allowed_chat_id}). Ctrl+C to stop.")
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("[Bot] stopped.")
    return 0


__all__ = ["TelegramBot", "run_bot"]
