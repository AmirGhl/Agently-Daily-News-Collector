from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import AppSettings
from .dashboard import load_catalog
from .html_report import render_html
from .markdown import render_markdown


def rerender_reports(
    *,
    settings: AppSettings,
    root_dir: Path,
    logger: logging.Logger,
) -> int:
    """Re-render every cataloged report's HTML (and Markdown) from its JSON
    with the current design. Lets design updates apply to old reports
    without re-running any collection or LLM work."""
    output_dir = root_dir / settings.output.directory
    count = 0
    for entry in load_catalog(output_dir):
        files = entry.get("files") or {}
        json_name = files.get("json")
        if not json_name:
            continue
        json_path = output_dir / str(json_name)
        try:
            report = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("[Rerender Skipped] unreadable %s", json_path.name)
            continue

        render_args = {
            "report_title": str(report.get("report_title") or "Report"),
            "generated_at": str(report.get("generated_at") or ""),
            "topic": str(report.get("topic") or ""),
            "language": str(report.get("language") or settings.workflow.output_language),
            "columns": [
                column for column in report.get("columns") or [] if isinstance(column, dict)
            ],
            "model_label": str(report.get("model") or ""),
            "tldr": [str(item) for item in report.get("tldr") or []],
        }
        html_name = files.get("html")
        if html_name:
            (output_dir / str(html_name)).write_text(
                render_html(**render_args), encoding="utf-8"
            )
        markdown_name = files.get("markdown")
        if markdown_name:
            (output_dir / str(markdown_name)).write_text(
                render_markdown(**render_args), encoding="utf-8"
            )
        count += 1
        logger.info("[Rerendered] %s", render_args["report_title"])
    return count


__all__ = ["rerender_reports"]
