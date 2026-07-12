from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import os
import re

from .config import MODEL_PRESETS, AppSettings
from .dashboard import load_catalog
from .logging_utils import configure_logging
from .webui_html import PAGE_HTML

CUSTOM_KEY_ENV = "CUSTOM_API_KEY"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}

_STATIC_CONTENT_TYPES = {
    **_CONTENT_TYPES,
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".map": "application/json",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}


def _find_static_dir(root_dir: Path) -> Path | None:
    """Locate the panel static files (./webui), bundled or local."""
    import sys

    candidates = []
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        candidates.append(Path(bundle_dir) / "webui")
    candidates.append(root_dir / "webui")
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


class _DequeLogHandler(logging.Handler):
    def __init__(self, sink: deque[str]):
        super().__init__(level=logging.INFO)
        self._sink = sink
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._sink.append(self.format(record))
        except Exception:
            pass


class WebUIServer:
    """Local control panel: start runs, watch progress, browse reports."""

    def __init__(self, *, root_dir: Path, settings_path: Path):
        self.root_dir = root_dir
        self.settings_path = settings_path
        self.static_dir = _find_static_dir(root_dir)
        self.log_lines: deque[str] = deque(maxlen=400)
        self.lock = threading.Lock()
        self.running = False
        self.current_topic: str | None = None
        self.last_error: str | None = None
        self.last_result_title: str | None = None
        self.logger = configure_logging(debug=False, log_dir=root_dir / "logs")
        self.logger.addHandler(_DequeLogHandler(self.log_lines))
        self.schedule_path = settings_path.parent / "schedule.json"
        
        # SSE progress streaming
        self.progress_queues: dict[str, asyncio.Queue] = {}
        self.progress_lock = threading.Lock()
        
        threading.Thread(target=self._schedule_loop, daemon=True).start()

    # ---- state helpers -------------------------------------------------

    def load_settings(self) -> AppSettings:
        return AppSettings.load(self.settings_path)

    def output_dir(self, settings: AppSettings | None = None) -> Path:
        resolved = settings or self.load_settings()
        return self.root_dir / resolved.output.directory

    def state(self) -> dict[str, Any]:
        try:
            settings = self.load_settings()
            language = settings.workflow.output_language
            topics = list(settings.topics)
            model_name = re.sub(
                r"\$\{\s*ENV\.([^}]+?)\s*\}",
                lambda match: os.getenv(match.group(1).strip(), "?"),
                settings.model.model,
            )
            model = (settings.model.preset or settings.model.provider) + " / " + model_name
        except Exception:
            language, topics, model = "English", [], ""
        with self.lock:
            return {
                "running": self.running,
                "topic": self.current_topic,
                "error": self.last_error,
                "last_report": self.last_result_title,
                "language": language,
                "topics": topics,
                "model": model,
                "log": list(self.log_lines)[-200:],
            }

    # ---- run orchestration ---------------------------------------------

    def start_run(self, params: dict[str, Any]) -> tuple[bool, str]:
        topic = str(params.get("topic") or "").strip()
        if params.get("dev") and not topic:
            from .dev_pulse import DEV_PULSE_TOPIC

            topic = DEV_PULSE_TOPIC
        if params.get("weekly") and not topic:
            from .weekly import WEEKLY_TOPIC

            topic = WEEKLY_TOPIC
        if not topic:
            return False, "topic_required"
        with self.lock:
            if self.running:
                return False, "already_running"
            self.running = True
            self.current_topic = topic
            self.last_error = None
        
        # Generate run_id for SSE tracking
        run_id = str(uuid.uuid4())[:8]
        self._current_run_id = run_id
        self._run_topics[run_id] = topic
        
        thread = threading.Thread(target=self._run, args=(topic, params, run_id), daemon=True)
        thread.start()
        return True, run_id

    def _run(self, topic: str, params: dict[str, Any], run_id: str) -> None:
        self._push_progress(run_id, "initializing", "Preparing run...", 5)
        
        from .collector import DailyNewsCollector
        from .delivery import deliver_report

        try:
            settings = self.load_settings()
            if params.get("dev"):
                from .dev_pulse import apply_dev_pulse

                apply_dev_pulse(settings)
            language = str(params.get("language") or "").strip()
            if language:
                settings.workflow.output_language = language
            self._push_progress(run_id, "config", "Configuration loaded", 10)

            # Fail fast when the model endpoint is down — otherwise the whole
            # flow runs to the end and quietly emits an empty report.
            self._push_progress(run_id, "model_check", "Checking model connection...", 15)
            probe = self.test_model_connection({})
            probe_message = str(probe.get("message") or "")
            # connection_failed = endpoint dead; http_5xx = endpoint up but sick
            # (Ollama answers 503 while it is starting/unhealthy). 4xx is left
            # alone: custom gateways may not implement /models at all.
            if not probe.get("ok") and (
                probe_message.startswith("connection_failed") or probe_message.startswith("http_5")
            ):
                self.logger.error(
                    "[Model Unreachable] %s — is the model server (e.g. Ollama) running?",
                    probe.get("message"),
                )
                with self.lock:
                    self.last_error = f"model_unreachable: {probe.get('message')}"
                self._push_progress(run_id, "error", "Model unreachable", 100)
                return
            self._push_progress(run_id, "model_ready", "Model connection OK", 20)

            if params.get("weekly"):
                self._push_progress(run_id, "weekly", "Generating weekly digest...", 30)
                import asyncio

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
                with self.lock:
                    if result is None:
                        self.last_error = "no_reports_last_7_days"
                    else:
                        self.last_result_title = str(result.get("report_title") or topic)
                self._push_progress(run_id, "complete", "Weekly digest ready", 100)
                return
            max_columns = params.get("max_columns")
            if isinstance(max_columns, int) and max_columns > 0:
                settings.workflow.max_column_num = max_columns
            max_news = params.get("max_news")
            if isinstance(max_news, int) and max_news > 0:
                settings.workflow.max_news_per_column = max_news
            if params.get("allow_repeats"):
                settings.history.filter_repeats = False

            from .collector import run_with_model_fallback

            self._push_progress(run_id, "collection", "Collecting news...", 30)
            result = run_with_model_fallback(
                settings=settings,
                root_dir=self.root_dir,
                logger=self.logger,
                topic=topic,
            )
            self._push_progress(run_id, "rendering", "Rendering report...", 80)
            if not (result.get("columns") or []):
                self.logger.error(
                    "[Empty Report] no columns were produced (model calls failed?) — "
                    "skipping delivery"
                )
                with self.lock:
                    self.last_error = "empty_report"
                self._push_progress(run_id, "error", "No columns produced", 100)
                return
            with self.lock:
                self.last_result_title = str(result.get("report_title") or topic)
            self._push_progress(run_id, "delivery", "Delivering report...", 90)
            if settings.delivery.telegram.enabled or settings.delivery.webhook.enabled:
                import asyncio

                asyncio.run(deliver_report(settings, result, self.logger))
            self._push_progress(run_id, "complete", "Report ready!", 100)
        except Exception as exc:
            self.logger.exception("WebUI run failed: %s", exc)
            with self.lock:
                self.last_error = str(exc)
            self._push_progress(run_id, "error", str(exc), 100)
        finally:
            with self.lock:
                self.running = False
                self.current_topic = None

    def _push_progress(self, run_id: str, step: str, detail: str, progress: int) -> None:
        """Push a progress update to the SSE queue for a run."""
        import asyncio
        queue = None
        with self.progress_lock:
            queue = self._progress_queues.get(run_id)
        if queue:
            try:
                # Use asyncio.run_coroutine_threadsafe to push to async queue from thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(queue.put({
                    "step": step,
                    "detail": detail,
                    "progress": progress,
                }))
                loop.close()
            except Exception:
                pass

    # ---- daily schedule --------------------------------------------------
    # Stored in its own schedule.json so it never interferes with the YAML
    # settings or settings.overrides.json. Fires only while the panel runs.

    def load_schedule(self) -> dict[str, Any]:
        try:
            data = json.loads(self.schedule_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
        return {}

    def schedule_view(self) -> dict[str, Any]:
        data = self.load_schedule()
        return {
            "enabled": bool(data.get("enabled")),
            "time": str(data.get("time") or "08:00"),
            "mode": str(data.get("mode") or "dev"),
            "topic": str(data.get("topic") or ""),
            "day": int(data.get("day", 4)),
            "last_fired": str(data.get("last_fired") or ""),
        }

    def save_schedule(self, params: dict[str, Any]) -> dict[str, Any]:
        time_str = str(params.get("time") or "08:00").strip()
        if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", time_str):
            return {"ok": False, "message": "bad_time"}
        mode = str(params.get("mode") or "dev").strip()
        if mode not in ("dev", "topic", "weekly"):
            return {"ok": False, "message": "bad_mode"}
        topic = str(params.get("topic") or "").strip()
        if mode == "topic" and not topic:
            return {"ok": False, "message": "topic_required"}
        try:
            day = int(params.get("day", 4))
        except (TypeError, ValueError):
            day = 4
        data = self.load_schedule()
        data.update(
            {
                "enabled": bool(params.get("enabled")),
                "time": time_str,
                "mode": mode,
                "topic": topic,
                "day": min(6, max(0, day)),
            }
        )
        try:
            self.schedule_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            return {"ok": False, "message": f"write_failed: {exc}"}
        self.logger.info(
            "[Schedule Saved] %s at %s (%s)",
            "enabled" if data["enabled"] else "disabled",
            time_str,
            mode,
        )
        return {"ok": True, "message": "saved", "schedule": self.schedule_view()}

    def _schedule_loop(self) -> None:
        import time as _time
        from datetime import datetime

        while True:
            _time.sleep(20)
            try:
                data = self.load_schedule()
                if not data.get("enabled"):
                    continue
                now = datetime.now()
                if now.strftime("%H:%M") != str(data.get("time") or ""):
                    continue
                today = now.strftime("%Y-%m-%d")
                if data.get("last_fired") == today:
                    continue
                mode = str(data.get("mode") or "dev")
                if mode == "weekly" and now.weekday() != int(data.get("day", 4)):
                    continue
                if mode == "dev":
                    params: dict[str, Any] = {"dev": True}
                elif mode == "weekly":
                    params = {"weekly": True}
                else:
                    params = {"topic": str(data.get("topic") or "")}
                ok, message = self.start_run(params)
                if ok or message != "already_running":
                    data["last_fired"] = today
                    self.schedule_path.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                self.logger.info("[Scheduled Run] mode=%s -> %s", mode, message)
            except Exception:
                pass

    # ---- settings management ---------------------------------------------

    def _overrides_path(self) -> Path:
        return self.settings_path.parent / "settings.overrides.json"

    def _env_path(self) -> Path:
        return self.root_dir / ".env"

    @staticmethod
    def _key_env_for(preset: str) -> str:
        if preset == "custom":
            return CUSTOM_KEY_ENV
        return MODEL_PRESETS.get(preset, {}).get("api_key_env", CUSTOM_KEY_ENV)

    def settings_view(self) -> dict[str, Any]:
        settings = self.load_settings()
        preset = settings.model.preset or ("custom" if "localhost" not in settings.model.base_url else "ollama")
        key_env = self._key_env_for(preset)
        from .dev_pulse import DEV_PULSE_SECTIONS
        return {
            "presets": [
                {
                    "id": name,
                    "default_model": meta["default_model"],
                    "key_env": meta["api_key_env"],
                    "available_models": meta.get("available_models", []),
                }
                for name, meta in MODEL_PRESETS.items()
            ],
            "current": {
                "preset": settings.model.preset or "",
                "model": settings.model.model,
                "base_url": settings.model.base_url,
                "language": settings.workflow.output_language,
                "tone": settings.workflow.tone,
                "max_columns": settings.workflow.max_column_num,
                "max_news": settings.workflow.max_news_per_column,
                "key_env": key_env,
                "key_present": bool(os.getenv(key_env)),
            },
            "topics": list(settings.topics),
            "delivery": {
                "telegram_enabled": settings.delivery.telegram.enabled,
                "chat_id": settings.delivery.telegram.chat_id or "",
                "send_html_file": settings.delivery.telegram.send_html_file,
                "send_style": settings.delivery.telegram.send_style,
                "proxy": settings.delivery.telegram.proxy or "",
                "token_present": bool(
                    settings.delivery.telegram.bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
                ),
            },
            "dev_pulse": {
                "reddit_subreddits": list(settings.dev_pulse.reddit_subreddits),
                "watch_repos": list(settings.dev_pulse.watch_repos),
                "extra_feeds": list(settings.dev_pulse.extra_feeds),
                "github_language": settings.dev_pulse.github_language or "",
                "enabled_sections": list(settings.dev_pulse.enabled_sections),
                "section_labels": [
                    {
                        "id": sid,
                        "title": sec["column_title"],
                        "description": sec.get("description", ""),
                    }
                    for sid, sec in DEV_PULSE_SECTIONS.items()
                ],
            },
        }

    def save_settings(self, params: dict[str, Any]) -> dict[str, Any]:
        import json

        preset = str(params.get("preset") or "").strip().lower()
        if preset and preset != "custom" and preset not in MODEL_PRESETS:
            return {"ok": False, "message": "unknown_preset"}

        model_override: dict[str, Any] = {}
        if preset == "custom":
            base_url = str(params.get("base_url") or "").strip()
            if not base_url:
                return {"ok": False, "message": "base_url_required"}
            model_override = {
                "preset": None,
                "base_url": base_url,
                "auth": {"api_key": f"${{{CUSTOM_KEY_ENV}}}"},
            }
        elif preset:
            model_override = {"preset": preset}
        model_name = str(params.get("model") or "").strip()
        if model_name:
            model_override["model"] = model_name

        overrides: dict[str, Any] = {}
        if self._overrides_path().exists():
            try:
                overrides = json.loads(self._overrides_path().read_text(encoding="utf-8"))
            except (OSError, ValueError):
                overrides = {}
        if not isinstance(overrides, dict):
            overrides = {}
        if model_override:
            overrides["MODEL"] = model_override
        workflow_override = dict(overrides.get("WORKFLOW") or {})
        for ui_key, yaml_key in (
            ("language", "output_language"),
            ("tone", "tone"),
            ("max_columns", "max_column_num"),
            ("max_news", "max_news_per_column"),
        ):
            value = params.get(ui_key)
            if value not in (None, ""):
                workflow_override[yaml_key] = value
        if workflow_override:
            overrides["WORKFLOW"] = workflow_override
        topics = params.get("topics")
        if isinstance(topics, list):
            overrides["TOPICS"] = [str(topic).strip() for topic in topics if str(topic).strip()]
        dev_params = params.get("dev_pulse")
        if isinstance(dev_params, dict):
            dev_override = dict(overrides.get("DEV_PULSE") or {})
            for key in ("reddit_subreddits", "watch_repos", "extra_feeds", "enabled_sections"):
                value = dev_params.get(key)
                if isinstance(value, list):
                    dev_override[key] = [str(v).strip() for v in value if str(v).strip()]
            if "github_language" in dev_params:
                dev_override["github_language"] = (
                    str(dev_params.get("github_language") or "").strip() or None
                )
            overrides["DEV_PULSE"] = dev_override
        delivery_params = params.get("delivery")
        if isinstance(delivery_params, dict):
            delivery_override = dict(overrides.get("DELIVERY") or {})
            telegram_block = dict(delivery_override.get("telegram") or {})
            telegram_block["enabled"] = bool(delivery_params.get("telegram_enabled"))
            telegram_block["chat_id"] = str(delivery_params.get("chat_id") or "").strip() or None
            telegram_block["send_html_file"] = bool(delivery_params.get("send_html_file"))
            send_style = str(delivery_params.get("send_style") or "").strip()
            if send_style in ("channel", "digest"):
                telegram_block["send_style"] = send_style
            telegram_block["proxy"] = str(delivery_params.get("proxy") or "").strip() or None
            bot_token = str(delivery_params.get("bot_token") or "").strip()
            if bot_token:
                # Token lives in .env only; overrides carry an env reference.
                self._write_env_var("TELEGRAM_BOT_TOKEN", bot_token)
                os.environ["TELEGRAM_BOT_TOKEN"] = bot_token
            if bot_token or os.getenv("TELEGRAM_BOT_TOKEN"):
                # Plain ${VAR} form: config's ENV_PATTERN resolves it from .env.
                # (${ENV.X} is a different, Agently-model-only syntax.)
                telegram_block["bot_token"] = "${TELEGRAM_BOT_TOKEN}"
            delivery_override["telegram"] = telegram_block
            overrides["DELIVERY"] = delivery_override
        self._overrides_path().write_text(
            json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        api_key = str(params.get("api_key") or "").strip()
        if api_key and preset:
            key_env = self._key_env_for(preset)
            self._write_env_var(key_env, api_key)
            os.environ[key_env] = api_key

        try:
            self.load_settings()
        except Exception as exc:
            return {"ok": False, "message": f"invalid_settings: {exc}"}
        self.logger.info("[Settings Saved] preset=%s model=%s", preset or "-", model_name or "-")
        return {"ok": True, "message": "saved"}

    def _write_env_var(self, name: str, value: str) -> None:
        env_path = self._env_path()
        lines: list[str] = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
        pattern = re.compile(rf"^\s*{re.escape(name)}\s*=")
        replaced = False
        for index, line in enumerate(lines):
            if pattern.match(line):
                lines[index] = f"{name}={value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{name}={value}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_model_connection(self, params: dict[str, Any]) -> dict[str, Any]:
        """Ping the provider's /models endpoint with the effective settings."""
        import httpx

        preset = str(params.get("preset") or "").strip().lower()
        if preset and preset in MODEL_PRESETS:
            base_url = MODEL_PRESETS[preset]["base_url"]
            key_env = MODEL_PRESETS[preset]["api_key_env"]
        elif preset == "custom":
            base_url = str(params.get("base_url") or "").strip()
            key_env = CUSTOM_KEY_ENV
        else:
            settings = self.load_settings()
            base_url = settings.model.base_url
            key_env = self._key_env_for(settings.model.preset or "custom")
        if not base_url:
            return {"ok": False, "message": "no_base_url"}

        api_key = str(params.get("api_key") or "").strip() or os.getenv(key_env, "")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            settings_now = self.load_settings()
            proxy = settings_now.proxy or None
        except Exception:
            proxy = None
        try:
            response = httpx.get(
                base_url.rstrip("/") + "/models",
                headers=headers,
                timeout=15.0,
                proxy=proxy,
            )
        except Exception as exc:
            return {"ok": False, "message": f"connection_failed: {type(exc).__name__}"}
        if response.status_code == 401:
            return {"ok": False, "message": "unauthorized"}
        if response.status_code >= 400:
            return {"ok": False, "message": f"http_{response.status_code}"}
        model_count = None
        try:
            payload = response.json()
            if isinstance(payload.get("data"), list):
                model_count = len(payload["data"])
        except ValueError:
            pass
        return {"ok": True, "message": "connected", "models": model_count}

    def test_telegram(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a real test message with the given (or saved) bot credentials."""
        import httpx

        token = str(params.get("bot_token") or "").strip()
        chat_id = str(params.get("chat_id") or "").strip()
        proxy = str(params.get("proxy") or "").strip() or None
        try:
            settings = self.load_settings()
            telegram = settings.delivery.telegram
            token = token or telegram.bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat_id = chat_id or telegram.chat_id or ""
            proxy = proxy or telegram.proxy or settings.proxy or None
        except Exception:
            token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            return {"ok": False, "message": "no_token"}
        if not chat_id:
            return {"ok": False, "message": "no_chat_id"}
        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "سردبیر ✓ اتصال تلگرام برقرار است.",
                    "disable_web_page_preview": True,
                },
                timeout=20.0,
                proxy=proxy,
            )
            data = response.json()
        except Exception as exc:
            return {"ok": False, "message": f"connection_failed: {type(exc).__name__}"}
        if data.get("ok"):
            return {"ok": True, "message": "sent"}
        return {"ok": False, "message": str(data.get("description") or f"http_{response.status_code}")}

    # ---- Windows autostart -----------------------------------------------
    # The scheduler only fires while the panel process is alive, so offer a
    # one-click "start with Windows" that drops a silent launcher into the
    # user's Startup folder (frozen exe only).

    def _startup_launcher_path(self) -> Path:
        appdata = os.getenv("APPDATA") or ""
        return (
            Path(appdata)
            / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            / "DailyNewsCollector.bat"
        )

    def autostart_view(self) -> dict[str, Any]:
        import sys

        supported = (
            os.name == "nt"
            and bool(getattr(sys, "frozen", False))
            and bool(os.getenv("APPDATA"))
        )
        return {
            "supported": supported,
            "enabled": supported and self._startup_launcher_path().exists(),
        }

    def set_autostart(self, params: dict[str, Any]) -> dict[str, Any]:
        import sys

        if not self.autostart_view()["supported"]:
            return {"ok": False, "message": "unsupported"}
        target = self._startup_launcher_path()
        enable = bool(params.get("enabled"))
        try:
            if enable:
                exe = Path(sys.executable).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    f'@echo off\nstart "" /min "{exe}" --ui --no-browser\n',
                    encoding="utf-8",
                )
            elif target.exists():
                target.unlink()
        except OSError as exc:
            return {"ok": False, "message": f"write_failed: {exc}"}
        self.logger.info("[Autostart] %s", "enabled" if enable else "disabled")
        return {"ok": True, "message": "saved", "autostart": self.autostart_view()}

    def send_report_to_telegram(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send an archived report to the configured Telegram chat on demand."""
        import asyncio

        name = str(params.get("json") or "").strip()
        report_file = self.resolve_report_file(name)
        if report_file is None or report_file.suffix.lower() != ".json":
            return {"ok": False, "message": "report_not_found"}
        try:
            result = json.loads(report_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"ok": False, "message": "unreadable_report"}
        if not isinstance(result, dict):
            return {"ok": False, "message": "unreadable_report"}
        try:
            settings = self.load_settings()
        except Exception as exc:
            return {"ok": False, "message": f"invalid_settings: {exc}"}
        telegram = settings.delivery.telegram
        if not (telegram.bot_token and telegram.chat_id):
            return {"ok": False, "message": "telegram_not_configured"}
        entry = next(
            (r for r in self.reports() if (r.get("files") or {}).get("json") == name), None
        )
        html_name = ((entry or {}).get("files") or {}).get("html")
        if html_name:
            html_file = self.resolve_report_file(html_name)
            if html_file is not None:
                result.setdefault("output_paths", {})["html"] = str(html_file)
        from .delivery import _deliver_to_telegram

        try:
            asyncio.run(
                _deliver_to_telegram(settings, result, telegram.proxy or settings.proxy or None)
            )
        except Exception as exc:
            return {"ok": False, "message": f"send_failed: {type(exc).__name__}"}
        self.logger.info("[Manual Telegram Send] %s", name)
        return {"ok": True, "message": "sent"}

    # ---- report files ---------------------------------------------------

    def reports(self) -> list[dict[str, Any]]:
        try:
            return load_catalog(self.output_dir())
        except Exception:
            return []

    def resolve_report_file(self, name: str) -> Path | None:
        output_dir = self.output_dir().resolve()
        candidate = (output_dir / name).resolve()
        if candidate.parent != output_dir:
            return None
        if candidate.suffix.lower() not in _CONTENT_TYPES:
            return None
        if not candidate.is_file():
            return None
        return candidate


def _make_handler(server_state: WebUIServer):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: Any, status: int = 200) -> None:
            self._send(
                status,
                "application/json; charset=utf-8",
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            )

        def _try_static(self, path: str) -> bool:
            static_dir = server_state.static_dir
            if static_dir is None:
                return False
            name = path.lstrip("/") or "index.html"
            candidate = (static_dir / name).resolve()
            try:
                candidate.relative_to(static_dir.resolve())
            except ValueError:
                return False
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.is_file() and not candidate.suffix:
                html_variant = candidate.with_suffix(".html")
                if html_variant.is_file():
                    candidate = html_variant
            if not candidate.is_file():
                return False
            content_type = _STATIC_CONTENT_TYPES.get(
                candidate.suffix.lower(), "application/octet-stream"
            )
            body = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if "/_next/" in path:
                self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            else:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return True

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                if not self._try_static(path):
                    self._send(200, "text/html; charset=utf-8", PAGE_HTML.encode("utf-8"))
            elif path == "/api/state":
                self._send_json(server_state.state())
            elif path == "/api/settings":
                self._send_json(server_state.settings_view())
            elif path == "/api/schedule":
                self._send_json(server_state.schedule_view())
            elif path == "/api/autostart":
                self._send_json(server_state.autostart_view())
            elif path == "/api/reports":
                self._send_json(server_state.reports())
            elif path.startswith("/reports/"):
                from urllib.parse import unquote

                name = unquote(path[len("/reports/"):])
                report_file = server_state.resolve_report_file(name)
                if report_file is None:
                    self._send_json({"error": "not_found"}, status=404)
                    return
                self._send(
                    200,
                    _CONTENT_TYPES[report_file.suffix.lower()],
                    report_file.read_bytes(),
                )
            elif self._try_static(path):
                pass
            elif path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            else:
                self._send_json({"error": "not_found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, TypeError):
                self._send_json({"error": "bad_request"}, status=400)
                return
            if not isinstance(payload, dict):
                payload = {}

            if path == "/api/run":
                ok, message = server_state.start_run(payload)
                if ok:
                    run_id = getattr(server_state, '_current_run_id', '')
                    self._send_json({"ok": ok, "message": message, "run_id": run_id}, status=200)
                else:
                    status = 200 if ok else (409 if message == "already_running" else 400)
                    self._send_json({"ok": ok, "message": message}, status=status)
            elif path == "/api/progress":
                # SSE endpoint for progress streaming
                run_id = None
                if "run_id=" in self.path:
                    run_id = self.path.split("run_id=")[1].split("&")[0]
                if run_id:
                    self._handle_sse_progress(server_state, run_id)
                else:
                    self._send_json({"error": "run_id required"}, status=400)
            elif path == "/api/settings":
                result = server_state.save_settings(payload)
                self._send_json(result, status=200 if result.get("ok") else 400)
            elif path == "/api/settings/test":
                self._send_json(server_state.test_model_connection(payload))
            elif path == "/api/schedule":
                result = server_state.save_schedule(payload)
                self._send_json(result, status=200 if result.get("ok") else 400)
            elif path == "/api/telegram/test":
                self._send_json(server_state.test_telegram(payload))
            elif path == "/api/telegram/send":
                self._send_json(server_state.send_report_to_telegram(payload))
            elif path == "/api/autostart":
                result = server_state.set_autostart(payload)
                self._send_json(result, status=200 if result.get("ok") else 400)
            else:
                self._send_json({"error": "not_found"}, status=404)

    return Handler


    def _handle_sse_progress(self, server_state: WebUIServer, run_id: str) -> None:
        """Handle SSE connection for progress streaming."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        # Create a queue for this run_id
        queue = asyncio.Queue()
        with server_state.progress_lock:
            server_state.progress_queues[run_id] = queue

        try:
            # Send initial connection message
            self.wfile.write(b"data: {\"type\": \"connected\", \"run_id\": \"" + run_id.encode() + b"\"}\n\n")
            self.wfile.flush()

            # Stream events from queue
            while True:
                try:
                    # Use asyncio.run_coroutine_threadsafe to get from async queue
                    import asyncio
                    future = asyncio.run_coroutine_threadsafe(queue.get(), asyncio.get_event_loop())
                    event = future.result(timeout=30)
                    if event is None:  # End signal
                        break
                    self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except asyncio.TimeoutError:
                    # Send keepalive
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                except Exception:
                    break
        except Exception:
            pass
        finally:
            # Clean up
            with server_state.progress_lock:
                server_state.progress_queues.pop(run_id, None)


def serve(
    *,
    root_dir: Path,
    settings_path: Path,
    port: int = 8899,
    open_browser: bool = True,
) -> int:
    state = WebUIServer(root_dir=root_dir, settings_path=settings_path)
    handler = _make_handler(state)

    httpd = None
    chosen_port = port
    for offset in range(20):
        chosen_port = port + offset
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", chosen_port), handler)
            break
        except OSError:
            continue
    if httpd is None:
        print(f"Could not bind a local port near {port}.")
        return 1

    url = f"http://127.0.0.1:{chosen_port}/"
    print(f"[WebUI] {url}  (Ctrl+C to stop)")
    state.logger.info("[WebUI Started] %s", url)
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[WebUI] stopped.")
    finally:
        httpd.server_close()
    return 0


__all__ = ["WebUIServer", "serve"]
