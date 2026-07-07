from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypeVar, cast

import yaml


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
LiteralStrT = TypeVar("LiteralStrT", bound=str)

ModelProvider: TypeAlias = Literal["OpenAICompatible", "OpenAI", "OAIClient"]
ModelType: TypeAlias = Literal["chat", "completions", "embeddings"]
SearchBackend: TypeAlias = Literal[
    "auto",
    "bing",
    "duckduckgo",
    "yahoo",
    "google",
    "mullvad_google",
    "yandex",
    "wikipedia",
]
SearchNewsTimeLimit: TypeAlias = Literal["d", "w", "m"]
SearchRegion: TypeAlias = Literal[
    "xa-ar",
    "xa-en",
    "ar-es",
    "au-en",
    "at-de",
    "be-fr",
    "be-nl",
    "br-pt",
    "bg-bg",
    "ca-en",
    "ca-fr",
    "ct-ca",
    "cl-es",
    "cn-zh",
    "co-es",
    "hr-hr",
    "cz-cs",
    "dk-da",
    "ee-et",
    "fi-fi",
    "fr-fr",
    "de-de",
    "gr-el",
    "hk-tzh",
    "hu-hu",
    "in-en",
    "id-id",
    "id-en",
    "ie-en",
    "il-he",
    "it-it",
    "jp-jp",
    "kr-kr",
    "lv-lv",
    "lt-lt",
    "xl-es",
    "my-ms",
    "my-en",
    "mx-es",
    "nl-nl",
    "nz-en",
    "no-no",
    "pe-es",
    "ph-en",
    "ph-tl",
    "pl-pl",
    "pt-pt",
    "ro-ro",
    "ru-ru",
    "sg-en",
    "sk-sk",
    "sl-sl",
    "za-en",
    "es-es",
    "se-sv",
    "ch-de",
    "ch-fr",
    "ch-it",
    "tw-tzh",
    "th-th",
    "tr-tr",
    "ua-uk",
    "uk-en",
    "us-en",
    "ue-es",
    "ve-es",
    "vn-vi",
]
BrowseResponseMode: TypeAlias = Literal["markdown", "text"]

MODEL_PROVIDER_VALUES: tuple[ModelProvider, ...] = ("OpenAICompatible", "OpenAI", "OAIClient")
MODEL_TYPE_VALUES: tuple[ModelType, ...] = ("chat", "completions", "embeddings")
SEARCH_BACKEND_VALUES: tuple[SearchBackend, ...] = (
    "auto",
    "bing",
    "duckduckgo",
    "yahoo",
    "google",
    "mullvad_google",
    "yandex",
    "wikipedia",
)
SEARCH_TIMELIMIT_VALUES: tuple[SearchNewsTimeLimit, ...] = ("d", "w", "m")
SEARCH_REGION_VALUES: tuple[SearchRegion, ...] = (
    "xa-ar",
    "xa-en",
    "ar-es",
    "au-en",
    "at-de",
    "be-fr",
    "be-nl",
    "br-pt",
    "bg-bg",
    "ca-en",
    "ca-fr",
    "ct-ca",
    "cl-es",
    "cn-zh",
    "co-es",
    "hr-hr",
    "cz-cs",
    "dk-da",
    "ee-et",
    "fi-fi",
    "fr-fr",
    "de-de",
    "gr-el",
    "hk-tzh",
    "hu-hu",
    "in-en",
    "id-id",
    "id-en",
    "ie-en",
    "il-he",
    "it-it",
    "jp-jp",
    "kr-kr",
    "lv-lv",
    "lt-lt",
    "xl-es",
    "my-ms",
    "my-en",
    "mx-es",
    "nl-nl",
    "nz-en",
    "no-no",
    "pe-es",
    "ph-en",
    "ph-tl",
    "pl-pl",
    "pt-pt",
    "ro-ro",
    "ru-ru",
    "sg-en",
    "sk-sk",
    "sl-sl",
    "za-en",
    "es-es",
    "se-sv",
    "ch-de",
    "ch-fr",
    "ch-it",
    "tw-tzh",
    "th-th",
    "tr-tr",
    "ua-uk",
    "uk-en",
    "us-en",
    "ue-es",
    "ve-es",
    "vn-vi",
)
BROWSE_RESPONSE_MODE_VALUES: tuple[BrowseResponseMode, ...] = ("markdown", "text")


def _resolve_env_placeholders(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            env_name = match.group(1)
            default_value = match.group(2) or ""
            return os.getenv(env_name, default_value)

        return ENV_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_resolve_env_placeholders(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _resolve_env_placeholders(item)
            for key, item in value.items()
        }
    return value


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _apply_ui_overrides(raw: dict[str, Any], overrides_path: Path) -> dict[str, Any]:
    """Overlay `settings.overrides.json` (written by the web panel) onto the
    YAML settings. Kept as a separate file so SETTINGS.yaml and its comments
    stay untouched by UI edits."""
    if not overrides_path.exists():
        return raw
    try:
        import json

        overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return raw
    if not isinstance(overrides, dict):
        return raw
    merged = dict(raw)
    for block_name, block_override in overrides.items():
        if not isinstance(block_override, dict):
            merged[block_name] = block_override
            continue
        base_block = dict(_as_dict(merged.get(block_name)))
        if block_name == "MODEL" and "preset" in block_override:
            # A preset choice must fully replace the model wiring; leftover
            # base_url/auth placeholders from the YAML would shadow it.
            request_options = base_block.get("request_options")
            base_block = {"request_options": request_options} if request_options else {}
        base_block.update(block_override)
        merged[block_name] = base_block
    return merged


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return ()
    result = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return tuple(result)


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _normalize_auth(value: Any) -> Any:
    if isinstance(value, str):
        normalized = _as_optional_str(value)
        if normalized and "input your api key" in normalized.lower():
            return None
        return normalized
    if isinstance(value, dict):
        normalized = {
            str(key): item
            for key, item in value.items()
            if item not in (None, "", [], {})
        }
        api_key = _as_optional_str(normalized.get("api_key"))
        if api_key is None:
            normalized.pop("api_key", None)
        else:
            normalized["api_key"] = api_key
        return normalized or None
    return value


def _as_literal(
    value: Any,
    *,
    allowed: tuple[LiteralStrT, ...],
    default: LiteralStrT,
) -> LiteralStrT:
    if isinstance(value, str):
        candidate = value.strip()
        if candidate in allowed:
            return cast(LiteralStrT, candidate)
        lower_candidate = candidate.lower()
        for item in allowed:
            if lower_candidate == item.lower():
                return item
    return default


# One-word presets for popular OpenAI-compatible providers. A preset fills
# base_url, the auth env-var, and a sensible default model; any MODEL.* key
# set explicitly still wins.
MODEL_PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4.1-mini",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "OLLAMA_API_KEY",
        "default_model": "qwen2.5:7b",
    },
}


@dataclass(slots=True)
class ModelConfig:
    provider: ModelProvider = "OpenAICompatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini"
    model_type: ModelType = "chat"
    auth: Any = None
    request_options: dict[str, Any] = field(default_factory=dict)
    proxy: str | None = None
    preset: str | None = None
    fallback_presets: tuple[str, ...] = ()

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "ModelConfig":
        block = _as_dict(raw.get("MODEL") or raw.get("model"))
        legacy_request_options = dict(_as_dict(raw.get("MODEL_OPTIONS")))
        block_request_options = dict(_as_dict(block.get("request_options") or block.get("options")))
        request_options = block_request_options or legacy_request_options

        preset_name = _as_optional_str(block.get("preset"))
        preset = MODEL_PRESETS.get(preset_name.lower()) if preset_name else None
        if preset_name and preset is None:
            raise ValueError(
                f"Unknown MODEL.preset {preset_name!r}. "
                f"Available presets: {', '.join(sorted(MODEL_PRESETS))}"
            )

        base_url = block.get("base_url") or raw.get("MODEL_URL")
        model_name = block.get("model") or request_options.pop("model", None)
        auth = block.get("auth", raw.get("MODEL_AUTH"))
        if preset is not None:
            base_url = base_url or preset["base_url"]
            model_name = model_name or os.getenv("AGENTLY_NEWS_MODEL") or preset["default_model"]
            if auth is None:
                auth = {"api_key": f"${{ENV.{preset['api_key_env']}}}"}

        primary_preset = preset_name.lower() if preset_name else None
        fallback_names: list[str] = []
        for name in _as_str_tuple(block.get("fallback_presets")):
            normalized_name = name.lower()
            if normalized_name not in MODEL_PRESETS:
                raise ValueError(
                    f"Unknown MODEL.fallback_presets entry {name!r}. "
                    f"Available presets: {', '.join(sorted(MODEL_PRESETS))}"
                )
            if normalized_name != primary_preset and normalized_name not in fallback_names:
                fallback_names.append(normalized_name)

        return cls(
            provider=_as_literal(
                block.get("provider") or raw.get("MODEL_PROVIDER"),
                allowed=MODEL_PROVIDER_VALUES,
                default="OpenAICompatible",
            ),
            base_url=str(base_url or "https://api.openai.com/v1"),
            model=str(model_name or "gpt-4.1-mini"),
            model_type=_as_literal(
                block.get("model_type"),
                allowed=MODEL_TYPE_VALUES,
                default="chat",
            ),
            auth=_normalize_auth(auth),
            request_options=request_options,
            proxy=_as_optional_str(block.get("proxy")),
            preset=primary_preset,
            fallback_presets=tuple(fallback_names),
        )

    @classmethod
    def for_preset(cls, name: str, *, proxy: str | None = None) -> "ModelConfig":
        """A fresh config wired to a preset's defaults (used for fallback runs)."""
        config = cls.from_raw({"MODEL": {"preset": name}})
        config.proxy = proxy
        return config

    def to_agently_settings(self, global_proxy: str | None = None) -> dict[str, Any]:
        settings: dict[str, Any] = {
            "base_url": self.base_url,
            "model": self.model,
            "model_type": self.model_type,
            "request_options": self.request_options,
        }
        proxy = self.proxy or global_proxy
        if proxy:
            settings["proxy"] = proxy
        if self.auth is not None:
            settings["auth"] = self.auth
        return settings


@dataclass(slots=True)
class SearchConfig:
    max_results: int = 8
    timelimit: SearchNewsTimeLimit = "d"
    region: SearchRegion = "us-en"
    backend: SearchBackend = "auto"
    rss_feeds: tuple[str, ...] = ()
    proxy: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "SearchConfig":
        block = _as_dict(raw.get("SEARCH") or raw.get("search"))
        return cls(
            max_results=max(_as_int(block.get("max_results", raw.get("MAX_SEARCH_RESULTS")), 8), 1),
            timelimit=_as_literal(
                block.get("timelimit"),
                allowed=SEARCH_TIMELIMIT_VALUES,
                default="d",
            ),
            region=_as_literal(
                block.get("region"),
                allowed=SEARCH_REGION_VALUES,
                default="us-en",
            ),
            backend=_as_literal(
                block.get("backend"),
                allowed=SEARCH_BACKEND_VALUES,
                default="auto",
            ),
            rss_feeds=_as_str_tuple(block.get("rss_feeds")),
            proxy=_as_optional_str(block.get("proxy")),
        )


@dataclass(slots=True)
class BrowseConfig:
    enable_playwright: bool = False
    playwright_headless: bool = True
    enable_jina_fallback: bool = True
    response_mode: BrowseResponseMode = "markdown"
    max_content_length: int = 12000
    min_content_length: int = 80
    proxy: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "BrowseConfig":
        block = _as_dict(raw.get("BROWSE") or raw.get("browse"))
        return cls(
            enable_playwright=_as_bool(block.get("enable_playwright"), False),
            playwright_headless=_as_bool(block.get("playwright_headless"), True),
            enable_jina_fallback=_as_bool(block.get("enable_jina_fallback"), True),
            response_mode=_as_literal(
                block.get("response_mode"),
                allowed=BROWSE_RESPONSE_MODE_VALUES,
                default="markdown",
            ),
            max_content_length=max(_as_int(block.get("max_content_length"), 12000), 2000),
            min_content_length=max(_as_int(block.get("min_content_length"), 80), 20),
            proxy=_as_optional_str(block.get("proxy")),
        )


WorkflowTone: TypeAlias = Literal["editorial", "conversational"]
WORKFLOW_TONE_VALUES: tuple[WorkflowTone, ...] = ("editorial", "conversational")


@dataclass(slots=True)
class WorkflowConfig:
    max_column_num: int = 3
    max_news_per_column: int = 3
    output_language: str = "Chinese"
    tone: WorkflowTone = "editorial"
    column_concurrency: int = 3
    summary_concurrency: int = 3

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "WorkflowConfig":
        block = _as_dict(raw.get("WORKFLOW") or raw.get("workflow"))
        return cls(
            max_column_num=max(_as_int(block.get("max_column_num", raw.get("MAX_COLUMN_NUM")), 3), 1),
            max_news_per_column=max(_as_int(block.get("max_news_per_column"), 3), 1),
            output_language=str(block.get("output_language") or raw.get("OUTPUT_LANGUAGE") or "Chinese"),
            tone=_as_literal(block.get("tone"), allowed=WORKFLOW_TONE_VALUES, default="editorial"),
            column_concurrency=max(_as_int(block.get("column_concurrency"), 3), 1),
            summary_concurrency=max(_as_int(block.get("summary_concurrency"), 3), 1),
        )


@dataclass(slots=True)
class OutlineConfig:
    use_customized: bool = False
    customized: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "OutlineConfig":
        block = _as_dict(raw.get("OUTLINE") or raw.get("outline"))
        customized = block.get("customized", raw.get("CUSTOMIZE_OUTLINE")) or {}
        return cls(
            use_customized=_as_bool(block.get("use_customized", raw.get("USE_CUSTOMIZE_OUTLINE", False))),
            customized=customized if isinstance(customized, dict) else {},
        )


OutputFormat: TypeAlias = Literal["markdown", "json", "html"]
OUTPUT_FORMAT_VALUES: tuple[OutputFormat, ...] = ("markdown", "json", "html")


@dataclass(slots=True)
class OutputConfig:
    directory: str = "outputs"
    formats: tuple[OutputFormat, ...] = ("markdown",)
    update_index: bool = True
    update_dashboard: bool = True
    # Absolute base URL for links in the generated RSS feed (outputs/feed.xml),
    # e.g. the GitHub Pages address. Falls back to the SITE_URL env var; when
    # empty, feed links stay relative.
    site_url: str = ""

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "OutputConfig":
        block = _as_dict(raw.get("OUTPUT") or raw.get("output"))
        return cls(
            directory=str(block.get("directory") or "outputs"),
            formats=cls._normalize_formats(block.get("formats")),
            update_index=_as_bool(block.get("update_index"), True),
            update_dashboard=_as_bool(block.get("update_dashboard"), True),
            site_url=str(block.get("site_url") or os.getenv("SITE_URL") or "").rstrip("/"),
        )

    @staticmethod
    def _normalize_formats(value: Any) -> tuple[OutputFormat, ...]:
        if isinstance(value, str):
            value = re.split(r"[\s,]+", value)
        candidates = value if isinstance(value, list) else []
        formats: list[OutputFormat] = []
        for item in candidates:
            normalized = _as_literal(item, allowed=OUTPUT_FORMAT_VALUES, default="markdown")
            if isinstance(item, str) and item.strip().lower() not in OUTPUT_FORMAT_VALUES:
                continue
            if normalized not in formats:
                formats.append(normalized)
        # Markdown is the canonical report body returned by the flow, so it is
        # always written even when the user only lists extra formats.
        if "markdown" not in formats:
            formats.insert(0, "markdown")
        return tuple(formats)


DEFAULT_WATCH_REPOS: tuple[str, ...] = (
    "ollama/ollama",
    "microsoft/vscode",
    "python/cpython",
    "nodejs/node",
    "anthropics/claude-code",
    "ggml-org/llama.cpp",
    "huggingface/transformers",
    "openai/codex",
    "google-gemini/gemini-cli",
    "langchain-ai/langchain",
    "vllm-project/vllm",
    "microsoft/TypeScript",
    "golang/go",
    "rust-lang/rust",
    "facebook/react",
    "vitejs/vite",
    "denoland/deno",
    "comfyanonymous/ComfyUI",
)
DEFAULT_SUBREDDITS: tuple[str, ...] = (
    "programming",
    "webdev",
    "LocalLLaMA",
    "MachineLearning",
    "artificial",
    "selfhosted",
    "netsec",
    "devops",
    "ExperiencedDevs",
)
DEFAULT_EXTRA_FEEDS: tuple[str, ...] = (
    "https://simonwillison.net/atom/everything/",
    "https://github.blog/feed/",
    "https://stackoverflow.blog/feed/",
    "https://newsletter.pragmaticengineer.com/feed",
)
SECURITY_SEVERITY_ORDER = ("low", "medium", "high", "critical")


@dataclass(slots=True)
class DevPulseConfig:
    reddit_subreddits: tuple[str, ...] = DEFAULT_SUBREDDITS
    min_hn_points: int = 80
    min_reddit_score: int = 100
    min_lobsters_score: int = 10
    min_devto_reactions: int = 20
    min_dailydev_upvotes: int = 20
    min_rising_stars: int = 30
    extra_feeds: tuple[str, ...] = DEFAULT_EXTRA_FEEDS
    github_language: str | None = None
    watch_repos: tuple[str, ...] = DEFAULT_WATCH_REPOS
    release_window_days: int = 3
    security_ecosystems: tuple[str, ...] = ("pip", "npm", "go", "rust", "maven")
    security_min_severity: str = "high"
    stack: tuple[str, ...] = ()

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "DevPulseConfig":
        block = _as_dict(raw.get("DEV_PULSE") or raw.get("dev_pulse"))
        subreddits = _as_str_tuple(block.get("reddit_subreddits"))
        watch_repos = (
            _as_str_tuple(block.get("watch_repos"))
            if "watch_repos" in block
            else DEFAULT_WATCH_REPOS
        )
        extra_feeds = (
            _as_str_tuple(block.get("extra_feeds"))
            if "extra_feeds" in block
            else DEFAULT_EXTRA_FEEDS
        )
        ecosystems = (
            _as_str_tuple(block.get("security_ecosystems"))
            if "security_ecosystems" in block
            else ("pip", "npm", "go", "rust", "maven")
        )
        severity = str(block.get("security_min_severity") or "high").strip().lower()
        if severity not in SECURITY_SEVERITY_ORDER:
            severity = "high"
        return cls(
            reddit_subreddits=subreddits or DEFAULT_SUBREDDITS,
            min_hn_points=max(_as_int(block.get("min_hn_points"), 80), 0),
            min_reddit_score=max(_as_int(block.get("min_reddit_score"), 100), 0),
            min_lobsters_score=max(_as_int(block.get("min_lobsters_score"), 10), 0),
            min_devto_reactions=max(_as_int(block.get("min_devto_reactions"), 20), 0),
            min_dailydev_upvotes=max(_as_int(block.get("min_dailydev_upvotes"), 20), 0),
            min_rising_stars=max(_as_int(block.get("min_rising_stars"), 30), 0),
            extra_feeds=extra_feeds,
            github_language=_as_optional_str(block.get("github_language")),
            watch_repos=watch_repos,
            release_window_days=max(_as_int(block.get("release_window_days"), 3), 1),
            security_ecosystems=ecosystems,
            security_min_severity=severity,
            stack=_as_str_tuple(block.get("stack")),
        )


@dataclass(slots=True)
class SummaryConfig:
    enable_tldr: bool = True

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "SummaryConfig":
        block = _as_dict(raw.get("SUMMARY") or raw.get("summary"))
        return cls(enable_tldr=_as_bool(block.get("enable_tldr"), True))


@dataclass(slots=True)
class HistoryConfig:
    enabled: bool = True
    retention_days: int = 30
    path: str = "outputs/.history.json"
    # When False, previously-published stories are kept in the report but
    # flagged is_new=False instead of being dropped (--allow-repeats).
    filter_repeats: bool = True

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "HistoryConfig":
        block = _as_dict(raw.get("HISTORY") or raw.get("history"))
        return cls(
            enabled=_as_bool(block.get("enabled"), True),
            retention_days=max(_as_int(block.get("retention_days"), 30), 1),
            path=str(block.get("path") or "outputs/.history.json"),
            filter_repeats=_as_bool(block.get("filter_repeats"), True),
        )


TelegramSendStyle: TypeAlias = Literal["channel", "digest"]
TELEGRAM_SEND_STYLE_VALUES: tuple[TelegramSendStyle, ...] = ("channel", "digest")


@dataclass(slots=True)
class TelegramDeliveryConfig:
    enabled: bool = False
    bot_token: str | None = None
    chat_id: str | None = None
    send_html_file: bool = True
    # channel = one post per story with photos (news-channel feel);
    # digest = the old packed multi-story messages.
    send_style: TelegramSendStyle = "channel"
    # Pause between channel-style posts (seconds) — reads naturally and stays
    # clear of Telegram's flood limits.
    message_delay: float = 1.8
    # Telegram-only proxy (e.g. socks5://127.0.0.1:10808) for networks where
    # api.telegram.org is blocked but the rest of the pipeline runs direct.
    proxy: str | None = None

    @classmethod
    def from_raw(cls, block: dict[str, Any]) -> "TelegramDeliveryConfig":
        try:
            message_delay = float(block.get("message_delay", 1.8))
        except (TypeError, ValueError):
            message_delay = 1.8
        return cls(
            enabled=_as_bool(block.get("enabled"), False),
            bot_token=_as_optional_str(block.get("bot_token")),
            chat_id=_as_optional_str(block.get("chat_id")),
            send_html_file=_as_bool(block.get("send_html_file"), True),
            send_style=_as_literal(
                block.get("send_style"),
                allowed=TELEGRAM_SEND_STYLE_VALUES,
                default="channel",
            ),
            message_delay=min(max(message_delay, 0.0), 15.0),
            proxy=_as_optional_str(block.get("proxy")),
        )


@dataclass(slots=True)
class WebhookDeliveryConfig:
    enabled: bool = False
    url: str | None = None

    @classmethod
    def from_raw(cls, block: dict[str, Any]) -> "WebhookDeliveryConfig":
        return cls(
            enabled=_as_bool(block.get("enabled"), False),
            url=_as_optional_str(block.get("url")),
        )


@dataclass(slots=True)
class DeliveryConfig:
    telegram: TelegramDeliveryConfig = field(default_factory=TelegramDeliveryConfig)
    webhook: WebhookDeliveryConfig = field(default_factory=WebhookDeliveryConfig)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "DeliveryConfig":
        block = _as_dict(raw.get("DELIVERY") or raw.get("delivery"))
        return cls(
            telegram=TelegramDeliveryConfig.from_raw(_as_dict(block.get("telegram"))),
            webhook=WebhookDeliveryConfig.from_raw(_as_dict(block.get("webhook"))),
        )


@dataclass(slots=True)
class AppSettings:
    debug: bool = False
    proxy: str | None = None
    topics: tuple[str, ...] = ()
    model: ModelConfig = field(default_factory=ModelConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    browse: BrowseConfig = field(default_factory=BrowseConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    outline: OutlineConfig = field(default_factory=OutlineConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    summary: SummaryConfig = field(default_factory=SummaryConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    dev_pulse: DevPulseConfig = field(default_factory=DevPulseConfig)

    @classmethod
    def load(cls, path: str | Path) -> "AppSettings":
        config_path = Path(path)
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise TypeError(f"Settings file must contain a dictionary, got: {type(raw)}")
        raw = _apply_ui_overrides(raw, config_path.parent / "settings.overrides.json")
        resolved = _resolve_env_placeholders(raw)
        return cls(
            debug=_as_bool(resolved.get("DEBUG", resolved.get("debug", False))),
            proxy=_as_optional_str(resolved.get("PROXY", resolved.get("proxy"))),
            topics=_as_str_tuple(resolved.get("TOPICS", resolved.get("topics"))),
            model=ModelConfig.from_raw(resolved),
            search=SearchConfig.from_raw(resolved),
            browse=BrowseConfig.from_raw(resolved),
            workflow=WorkflowConfig.from_raw(resolved),
            outline=OutlineConfig.from_raw(resolved),
            output=OutputConfig.from_raw(resolved),
            summary=SummaryConfig.from_raw(resolved),
            history=HistoryConfig.from_raw(resolved),
            delivery=DeliveryConfig.from_raw(resolved),
            dev_pulse=DevPulseConfig.from_raw(resolved),
        )
