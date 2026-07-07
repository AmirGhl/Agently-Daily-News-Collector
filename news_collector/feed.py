"""RSS 2.0 feed generated from the reports catalog (outputs/reports.json).

Written next to the dashboard so anyone can subscribe to the briefings with
a feed reader once the outputs directory is hosted (e.g. on GitHub Pages).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

FEED_FILE_NAME = "feed.xml"
MAX_FEED_ITEMS = 50


def _rfc822(value: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%a, %d %b %Y %H:%M:%S +0000")
        except ValueError:
            continue
    return ""


def _entry_link(entry: dict[str, Any], site_url: str) -> str:
    files = entry.get("files") if isinstance(entry.get("files"), dict) else {}
    file_name = files.get("html") or files.get("markdown") or ""
    if not file_name:
        return ""
    encoded = quote(str(file_name))
    return f"{site_url}/{encoded}" if site_url else encoded


def render_feed(
    catalog: list[dict[str, Any]],
    *,
    site_url: str = "",
    title: str = "Daily News Collector",
    description: str = "AI-generated daily news briefings.",
) -> str:
    site_url = site_url.rstrip("/")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        f"<title>{escape(title)}</title>",
        f"<link>{escape(site_url or '.')}</link>",
        f"<description>{escape(description)}</description>",
        f"<lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>",
    ]
    if site_url:
        parts.append(
            f'<atom:link href="{escape(site_url)}/{FEED_FILE_NAME}" '
            'rel="self" type="application/rss+xml"/>'
        )
    for entry in catalog[:MAX_FEED_ITEMS]:
        report_title = str(entry.get("report_title") or "Untitled briefing")
        link = _entry_link(entry, site_url)
        topic = str(entry.get("topic") or "")
        date = str(entry.get("generated_at") or entry.get("date") or "")
        parts.append("<item>")
        parts.append(f"<title>{escape(report_title)}</title>")
        if link:
            parts.append(f"<link>{escape(link)}</link>")
            permalink = "true" if site_url else "false"
            parts.append(f'<guid isPermaLink="{permalink}">{escape(link)}</guid>')
        if topic:
            parts.append(f"<description>{escape(topic)}</description>")
            parts.append(f"<category>{escape(topic)}</category>")
        pub_date = _rfc822(date)
        if pub_date:
            parts.append(f"<pubDate>{pub_date}</pubDate>")
        parts.append("</item>")
    parts.extend(["</channel>", "</rss>"])
    return "\n".join(parts) + "\n"


def write_feed(
    output_dir: str | Path,
    catalog: list[dict[str, Any]],
    *,
    site_url: str = "",
) -> Path:
    resolved_dir = Path(output_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)
    feed_path = resolved_dir / FEED_FILE_NAME
    feed_path.write_text(render_feed(catalog, site_url=site_url), encoding="utf-8")
    return feed_path


__all__ = ["FEED_FILE_NAME", "render_feed", "write_feed"]
