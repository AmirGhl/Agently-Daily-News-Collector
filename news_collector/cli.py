from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv

from .config import OUTPUT_FORMAT_VALUES, AppSettings
from .collector import DailyNewsCollector, run_with_model_fallback
from .delivery import deliver_report
from .logging_utils import configure_logging
from .markdown import render_markdown
from .html_report import render_html


def merge_reports(reports: list[dict[str, Any]], topics: list[str]) -> dict[str, Any]:
    """Merge multiple single-topic reports into one multi-topic report."""
    if not reports:
        return {}

    # Use the first report as base
    base = reports[0].copy()
    
    # Merge all columns with topic prefix
    all_columns = []
    all_tldr = []
    
    for i, report in enumerate(reports):
        topic = topics[i] if i < len(topics) else f"Topic {i+1}"
        report_tldr = report.get("tldr") or []
        # Prefix TL;DR items with topic
        for item in report_tldr:
            all_tldr.append(f"[{topic}] {item}")
        
        # Add topic header to each column
        columns = report.get("columns") or []
        for column in columns:
            if not isinstance(column, dict):
                continue
            col_title = column.get("title", "")
            column = dict(column)
            column["title"] = f"{topic} · {col_title}"
            all_columns.append(column)

    # Generate merged report
    now = asyncio.get_event_loop().time() if False else __import__("datetime").datetime.now()
    from datetime import datetime
    now = datetime.now()
    
    merged_report = {
        "report_title": base.get("report_title", "Multi-Topic Report"),
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "topic": ", ".join(topics),
        "language": base.get("language", "English"),
        "model": base.get("model", ""),
        "tldr": all_tldr,
        "columns": all_columns,
    }
    
    return merged_report


def run_multi_topic_merge(
    topics: list[str],
    settings: AppSettings,
    root_dir: Path,
    logger,
    args: argparse.Namespace,
) -> int:
    """Run collection for multiple topics in parallel and merge results."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    logger.info("[Multi-Topic] Running %d topics in parallel: %s", len(topics), topics)
    
    def collect_single(topic: str) -> tuple[str, dict[str, Any] | None, Exception | None]:
        try:
            result = run_with_model_fallback(
                settings=settings,
                root_dir=root_dir,
                logger=logger,
                topic=topic,
            )
            return topic, result, None
        except Exception as exc:
            logger.exception("Multi-topic collection failed for %r: %s", topic, exc)
            return topic, None, exc
    
    results: list[dict[str, Any]] = []
    successful_topics: list[str] = []
    
    with ThreadPoolExecutor(max_workers=min(len(topics), 4)) as executor:
        futures = {executor.submit(collect_single, t): t for t in topics}
        for future in as_completed(futures):
            topic, result, exc = future.result()
            if exc or result is None:
                logger.error("[Multi-Topic] Topic %r failed", topic)
                continue
            results.append(result)
            successful_topics.append(topic)
    
    if not results:
        logger.error("[Multi-Topic] All topics failed")
        return 1
    
    # Merge reports
    merged = merge_reports(results, successful_topics)
    
    # Render outputs
    from datetime import datetime
    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    
    markdown = render_markdown(
        report_title=merged["report_title"],
        generated_at=merged["generated_at"],
        topic=merged["topic"],
        language=merged["language"],
        columns=merged["columns"],
        model_label=results[0].get("model", ""),
        tldr=merged["tldr"],
    )
    
    # Save merged report
    output_dir = root_dir / settings.output.directory
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in merged["report_title"]).strip()
    base_name = f"{safe_title}_{report_date}_multi"
    
    markdown_path = output_dir / f"{base_name}.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    
    # Save JSON
    import json
    json_path = output_dir / f"{base_name}.json"
    json_data = {
        "report_title": merged["report_title"],
        "generated_at": merged["generated_at"],
        "topic": merged["topic"],
        "language": merged["language"],
        "model": merged["model"],
        "tldr": merged["tldr"],
        "columns": merged["columns"],
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Render HTML
    html = render_html(
        report_title=merged["report_title"],
        generated_at=merged["generated_at"],
        topic=merged["topic"],
        language=merged["language"],
        columns=merged["columns"],
        model_label=results[0].get("model", ""),
        tldr=merged["tldr"],
    )
    html_path = output_dir / f"{base_name}.html"
    html_path.write_text(html, encoding="utf-8")
    
    # Update dashboard
    from .dashboard import update_dashboard
    update_dashboard(
        output_dir=output_dir,
        entry={
            "report_title": merged["report_title"],
            "topic": merged["topic"],
            "language": merged["language"],
            "date": report_date,
            "generated_at": merged["generated_at"],
            "files": {
                "markdown": markdown_path.name,
                "json": json_path.name,
                "html": html_path.name,
            },
        },
        site_url=settings.output.site_url,
    )
    
    # Delivery
    if settings.delivery.telegram.enabled or settings.delivery.webhook.enabled:
        merged["output_paths"] = {"markdown": str(markdown_path), "json": str(json_path), "html": str(html_path)}
        try:
            delivered = asyncio.run(deliver_report(settings, merged, logger))
            for dest in delivered:
                logger.info("[Delivered] %s", dest)
        except Exception as exc:
            logger.warning("[Multi-Topic Delivery Failed] %s", exc)
    
    if not args.quiet:
        print(merged.get("markdown", markdown))
    
    for path in [markdown_path, json_path, html_path]:
        print(f"[Saved {path.suffix[1:].upper()}] {path}")
    
    return 0


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
        "--topics",
        type=str,
        help="comma-separated list of topics to run in parallel and merge into one report",
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
        "--bot",
        action="store_true",
        help="run the two-way Telegram bot: reply to /news, /dev and /weekly commands",
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
        # Keep tracking history but stop filtering: repeated stories flow
        # through flagged is_new=False so reports can badge the fresh ones.
        settings.history.filter_repeats = False
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

    if args.bot:
        from .telegram_bot import run_bot

        return run_bot(
            settings_path=Path(args.settings),
            root_dir=ROOT_DIR,
            logger=logger,
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

    # Handle multi-topic merge mode
    if args.topics:
        topics = [t.strip() for t in args.topics.split(",") if t.strip()]
        if not topics:
            print("No valid topics provided in --topics.")
            return 1
        return run_multi_topic_merge(topics, settings, ROOT_DIR, logger, args)

    failures = 0
    for topic in topics:
        # A fresh collector per topic keeps every TriggerFlow single-use;
        # run_with_model_fallback retries with MODEL.fallback_presets on failure.
        try:
            result = run_with_model_fallback(
                settings=settings,
                root_dir=ROOT_DIR,
                logger=logger,
                topic=topic,
            )
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
