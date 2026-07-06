from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from .config import OUTPUT_FORMAT_VALUES, AppSettings
from .collector import DailyNewsCollector
from .delivery import deliver_report
from .logging_utils import configure_logging


def _resolve_root_dir() -> Path:
    # In a PyInstaller build, work next to the executable so SETTINGS.yaml,
    # prompts/, outputs/, and logs/ stay visible and editable by the user.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _ensure_runtime_files(root_dir: Path) -> None:
    """First-run setup for the frozen executable: extract the bundled
    default SETTINGS.yaml and prompts/ next to the exe if missing."""
    bundle_dir = Path(getattr(sys, "_MEIPASS", ""))
    if not bundle_dir or not bundle_dir.exists():
        return
    settings_target = root_dir / "SETTINGS.yaml"
    settings_source = bundle_dir / "SETTINGS.yaml"
    if not settings_target.exists() and settings_source.exists():
        shutil.copyfile(settings_source, settings_target)
        print(f"[First Run] Default settings written to {settings_target}")
    prompts_target = root_dir / "prompts"
    prompts_source = bundle_dir / "prompts"
    if not prompts_target.exists() and prompts_source.exists():
        shutil.copytree(prompts_source, prompts_target)
        print(f"[First Run] Prompt templates written to {prompts_target}")


ROOT_DIR = _resolve_root_dir()
SETTINGS_PATH = ROOT_DIR / "SETTINGS.yaml"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agently-news",
        description="Generate a multi-column daily news briefing about a topic.",
    )
    parser.add_argument(
        "topic",
        nargs="*",
        help="topic to collect news about (prompted interactively if omitted)",
    )
    parser.add_argument(
        "-s",
        "--settings",
        type=Path,
        default=SETTINGS_PATH,
        help="path to a SETTINGS.yaml file (default: project SETTINGS.yaml)",
    )
    parser.add_argument(
        "-l",
        "--language",
        help="output language, e.g. English, Chinese, Persian",
    )
    parser.add_argument(
        "-c",
        "--max-columns",
        type=int,
        help="maximum number of report columns",
    )
    parser.add_argument(
        "-n",
        "--max-news",
        type=int,
        help="maximum news stories per column",
    )
    parser.add_argument(
        "-f",
        "--formats",
        nargs="+",
        choices=list(OUTPUT_FORMAT_VALUES),
        help="output file formats (markdown is always written)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="directory for generated reports",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="run every topic listed under TOPICS in the settings file",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="developer pulse mode: GitHub trending/new repos, releases, "
        "security advisories, Hacker News, Reddit, Lobsters, and dev.to",
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="synthesize the last 7 days of reports into one weekly digest",
    )
    parser.add_argument(
        "--rerender",
        action="store_true",
        help="re-render all existing reports' HTML/Markdown with the current design (no LLM)",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="open the local web control panel (default when the exe is double-clicked)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8899,
        help="port for the web control panel (default: 8899)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="with --ui: start the panel without opening a browser tab (autostart)",
    )
    parser.add_argument(
        "--allow-repeats",
        action="store_true",
        help="allow stories that already appeared in previous reports",
    )
    parser.add_argument(
        "--no-tldr",
        action="store_true",
        help="skip the key-takeaways summary at the top of the report",
    )
    parser.add_argument(
        "--no-deliver",
        action="store_true",
        help="skip Telegram/webhook delivery even if enabled in settings",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug logging",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only the saved file paths, not the full report",
    )
    return parser


def _apply_overrides(settings: AppSettings, args: argparse.Namespace) -> None:
    if args.language:
        settings.workflow.output_language = args.language
    if args.max_columns is not None:
        settings.workflow.max_column_num = max(args.max_columns, 1)
    if args.max_news is not None:
        settings.workflow.max_news_per_column = max(args.max_news, 1)
    if args.formats:
        formats = list(dict.fromkeys(args.formats))
        if "markdown" not in formats:
            formats.insert(0, "markdown")
        settings.output.formats = tuple(formats)
    if args.output_dir:
        settings.output.directory = args.output_dir
    if args.allow_repeats:
        settings.history.enabled = False
    if args.no_tldr:
        settings.summary.enable_tldr = False
    if args.no_deliver:
        settings.delivery.telegram.enabled = False
        settings.delivery.webhook.enabled = False
    if args.debug:
        settings.debug = True


def main() -> int:
    args = build_arg_parser().parse_args()
    _ensure_runtime_files(ROOT_DIR)
    # Load .env before reading SETTINGS.yaml so ${VAR} placeholders
    # (e.g. Telegram credentials) resolve from the local .env file too.
    load_dotenv(find_dotenv())
    env_next_to_exe = ROOT_DIR / ".env"
    if env_next_to_exe.exists():
        load_dotenv(env_next_to_exe, override=False)

    # Double-clicking the exe (no arguments) should land in the control
    # panel instead of a bare console prompt.
    if args.ui or (getattr(sys, "frozen", False) and len(sys.argv) == 1):
        from .webui import serve

        return serve(
            root_dir=ROOT_DIR,
            settings_path=Path(args.settings),
            port=args.port,
            open_browser=not args.no_browser,
        )

    settings = AppSettings.load(args.settings)
    _apply_overrides(settings, args)
    logger = configure_logging(
        debug=settings.debug,
        log_dir=ROOT_DIR / "logs",
    )

    if args.rerender:
        from .rerender import rerender_reports

        count = rerender_reports(settings=settings, root_dir=ROOT_DIR, logger=logger)
        print(f"Re-rendered {count} report(s) with the current design.")
        return 0

    if args.weekly:
        import asyncio as _asyncio

        from .weekly import generate_weekly_digest

        collector = DailyNewsCollector(settings=settings, root_dir=ROOT_DIR, logger=logger)
        try:
            result = _asyncio.run(
                generate_weekly_digest(
                    settings=settings,
                    root_dir=ROOT_DIR,
                    logger=logger,
                    model_label=collector.model_label,
                )
            )
        except Exception as exc:  # pragma: no cover - CLI guard
            logger.exception("Weekly digest failed: %s", exc)
            return 1
        if result is None:
            print("No reports from the last 7 days to digest.")
            return 1
        if not args.quiet:
            print(result["markdown"])
        for output_format, path in result["output_paths"].items():
            print(f"[Saved {output_format}] {path}")
        return 0

    if args.dev:
        from .dev_pulse import DEV_PULSE_TOPIC, apply_dev_pulse

        apply_dev_pulse(settings)
        topics = [" ".join(args.topic).strip() or DEV_PULSE_TOPIC]
    elif args.all:
        topics = list(settings.topics)
        if not topics:
            print("No TOPICS configured in the settings file; nothing to run with --all.")
            return 1
    else:
        topic = " ".join(args.topic).strip()
        if not topic:
            topic = input("请输入要生成新闻汇总的主题 / Please input the topic: ").strip()
        if not topic:
            print("Topic is required.")
            return 1
        topics = [topic]

    failures = 0
    for topic in topics:
        # A fresh collector per topic keeps every TriggerFlow single-use.
        collector = DailyNewsCollector(
            settings=settings,
            root_dir=ROOT_DIR,
            logger=logger,
        )
        try:
            result = collector.collect(topic)
        except Exception as exc:  # pragma: no cover - CLI guard
            logger.exception("Daily news collection failed for %r: %s", topic, exc)
            failures += 1
            continue

        if not args.quiet:
            print(result["markdown"])
        output_paths = result.get("output_paths") or {"markdown": result["output_path"]}
        for output_format, path in output_paths.items():
            print(f"[Saved {output_format}] {path}")

        if settings.delivery.telegram.enabled or settings.delivery.webhook.enabled:
            delivered = asyncio.run(deliver_report(settings, result, logger))
            for destination in delivered:
                print(f"[Delivered] {destination}")

    return 1 if failures == len(topics) else 0
