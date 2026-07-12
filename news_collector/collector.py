from __future__ import annotations

import copy
import logging
import os
import re
from pathlib import Path
from typing import Any

from agently import Agently

from tools import create_browse_tool, create_dev_sources_tool, create_rss_tool, create_search_tool
from workflow import build_daily_news_flow

from .alerts import AlertEngine, build_alert_config
from .config import AppSettings, ModelConfig


class DailyNewsCollector:
    def __init__(
        self,
        *,
        settings: AppSettings,
        root_dir: str | Path,
        logger: logging.Logger,
    ):
        self.settings = settings
        self.root_dir = Path(root_dir).resolve()
        self.logger = logger

        self._configure_agently()

        search_tool = create_search_tool(self.settings)
        browse_tool = create_browse_tool(self.settings)
        rss_tool = create_rss_tool(self.settings)
        self.flow = build_daily_news_flow(
            settings=self.settings,
            root_dir=self.root_dir,
            model_label=self.model_label,
        )
        self.flow.update_runtime_resources(
            logger=self.logger,
            search_tool=search_tool,
            browse_tool=browse_tool,
            rss_tool=rss_tool,
            dev_sources_tool=create_dev_sources_tool(self.settings, root_dir=self.root_dir),
        )

    def collect(self, topic: str) -> dict[str, Any]:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise ValueError("Topic is required.")
        snapshot = self.flow.start(normalized_topic)
        if isinstance(snapshot, dict):
            final = snapshot.get("$final_result")
            if isinstance(final, dict):
                # Process breaking alerts after successful collection
                self._process_breaking_alerts(final, normalized_topic)
                return final
            if "markdown" in snapshot:
                self._process_breaking_alerts(snapshot, normalized_topic)
                return snapshot
        raise RuntimeError(
            f"Flow produced no valid result. "
            f"Snapshot keys: {list(snapshot.keys()) if isinstance(snapshot, dict) else type(snapshot)}"
        )

    def _process_breaking_alerts(self, report: dict[str, Any], topic: str) -> None:
        """Check report stories for breaking news and send alerts."""
        if not self.settings.delivery.telegram.enabled and not self.settings.delivery.webhook.enabled:
            return

        try:
            alert_config = build_alert_config(self.settings)
            if not alert_config.enabled:
                return

            engine = AlertEngine(alert_config)
            columns = report.get("columns") or []
            for column in columns:
                if not isinstance(column, dict):
                    continue
                for story in column.get("news_list") or []:
                    if not isinstance(story, dict):
                        continue
                    should_alert, match = engine.should_alert(story, topic)
                    if should_alert:
                        self.logger.info(
                            "[Breaking Alert] %s: %s (severity=%d, keywords=%s)",
                            topic,
                            story.get("title", "")[:80],
                            match.severity,
                            match.matched_keywords,
                        )
                        # Fire-and-forget alert delivery
                        self._deliver_alert(report, story, match, alert_config.channels)
        except Exception as exc:
            self.logger.warning("[Alert Processing Failed] %s", exc)

    def _deliver_alert(
        self,
        report: dict[str, Any],
        story: dict[str, Any],
        match: Any,
        channels: tuple[str, ...],
    ) -> None:
        """Deliver breaking alert via configured channels."""
        import asyncio

        from .delivery import deliver_alert

        alert_data = {
            "report_title": report.get("report_title", "Breaking News"),
            "generated_at": report.get("generated_at", ""),
            "topic": report.get("topic", ""),
            "story": story,
            "match": {
                "keywords": match.matched_keywords,
                "cve_ids": match.cve_ids,
                "severity": match.severity,
            },
        }

        try:
            asyncio.run(deliver_alert(self.settings, alert_data, channels))
        except Exception as exc:
            self.logger.warning("[Alert Delivery Failed] %s", exc)

    def _configure_agently(self) -> None:
        from dotenv import find_dotenv, load_dotenv

        load_dotenv(find_dotenv())
        model_settings = self.settings.model.to_agently_settings(self.settings.proxy)
        self._ensure_required_model_env(
            {
                "base_url": model_settings.get("base_url"),
                "model": model_settings.get("model"),
            }
        )
        missing_auth_envs = self._missing_env_names(model_settings.get("auth"))
        if missing_auth_envs:
            # Cloud presets require a key; local endpoints (ollama) can run
            # without auth, so just drop the block there.
            if self.settings.model.preset not in (None, "ollama"):
                raise EnvironmentError(
                    f"MODEL.preset '{self.settings.model.preset}' needs "
                    + ", ".join(missing_auth_envs)
                    + " set in the environment or .env file."
                )
            model_settings.pop("auth", None)

        resolved_model_name = self._resolve_env_value(model_settings.get("model"))
        self.model_label = f"{self.settings.model.provider} / {resolved_model_name}"
        Agently.set_settings("debug", self.settings.debug)
        Agently.set_settings(
            self.settings.model.provider,
            model_settings,
            auto_load_env=True,
        )

    def _ensure_required_model_env(self, model_settings: dict[str, Any]) -> None:
        env_names = sorted(set(self._collect_env_names(model_settings)))
        if not env_names:
            return

        missing_env_names = [
            name for name in env_names if os.getenv(name) in (None, "")
        ]
        if missing_env_names:
            raise EnvironmentError(
                "Missing required model environment variables: "
                + ", ".join(missing_env_names)
            )

    @classmethod
    def _collect_env_names(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return re.findall(r"\$\{\s*ENV\.([^}]+?)\s*\}", value)
        env_names: list[str] = []
        if isinstance(value, dict):
            for item in value.values():
                env_names.extend(cls._collect_env_names(item))
        elif isinstance(value, list):
            for item in value:
                env_names.extend(cls._collect_env_names(item))
        return env_names

    @classmethod
    def _missing_env_names(cls, value: Any) -> list[str]:
        env_names = sorted(set(cls._collect_env_names(value)))
        return [name for name in env_names if os.getenv(name) in (None, "")]

    @staticmethod
    def _resolve_env_value(value: Any) -> str:
        if not isinstance(value, str):
            return str(value)

        def replacer(match: re.Match[str]) -> str:
            env_name = match.group(1).strip()
            return os.getenv(env_name, match.group(0))

        return re.sub(r"\$\{\s*ENV\.([^}]+?)\s*\}", replacer, value)


def run_with_model_fallback(
    *,
    settings: AppSettings,
    root_dir: str | Path,
    logger: logging.Logger,
    topic: str,
) -> dict[str, Any]:
    """Collect with the primary model, then each MODEL.fallback_presets entry.

    A fallback preset with a missing API key is skipped (its constructor
    raises before any network call). If every attempt fails, the primary
    model's error is re-raised - it is the one the user cares about.
    """
    attempts: list[str | None] = [None, *settings.model.fallback_presets]
    primary_exc: Exception | None = None
    for index, preset in enumerate(attempts):
        run_settings = settings
        if preset is not None:
            run_settings = copy.deepcopy(settings)
            run_settings.model = ModelConfig.for_preset(preset, proxy=settings.model.proxy)
            logger.warning(
                "[Model Fallback] trying preset %r (%d of %d fallbacks)",
                preset,
                index,
                len(attempts) - 1,
            )
        try:
            collector = DailyNewsCollector(
                settings=run_settings,
                root_dir=root_dir,
                logger=logger,
            )
            result = collector.collect(topic)
            if preset is not None:
                logger.warning("[Model Fallback] preset %r produced the report", preset)
            return result
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            if primary_exc is None:
                primary_exc = exc
            if index < len(attempts) - 1:
                logger.warning("[Model Failed] %s - trying next fallback", exc)
    assert primary_exc is not None
    raise primary_exc
