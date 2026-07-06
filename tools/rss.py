from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from news_collector.config import AppSettings, SearchNewsTimeLimit

_TIMELIMIT_DAYS = {"d": 1, "w": 7, "m": 30}
_ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _parse_date(raw: str) -> datetime | None:
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _text(element: ET.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def parse_feed(content: str) -> list[dict[str, str]]:
    """Parse RSS 2.0 or Atom into normalized news dicts."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    items: list[dict[str, str]] = []
    if root.tag == f"{_ATOM_NS}feed":
        source = _text(root.find(f"{_ATOM_NS}title"))
        for entry in root.findall(f"{_ATOM_NS}entry"):
            link = ""
            for link_el in entry.findall(f"{_ATOM_NS}link"):
                if link_el.get("rel") in (None, "alternate"):
                    link = str(link_el.get("href") or "")
                    break
            items.append(
                {
                    "title": _text(entry.find(f"{_ATOM_NS}title")),
                    "url": link.strip(),
                    "body": _text(entry.find(f"{_ATOM_NS}summary"))
                    or _text(entry.find(f"{_ATOM_NS}content")),
                    "date": _text(entry.find(f"{_ATOM_NS}published"))
                    or _text(entry.find(f"{_ATOM_NS}updated")),
                    "source": source,
                }
            )
    else:
        channel = root.find("channel")
        if channel is None:
            return []
        source = _text(channel.find("title"))
        for item in channel.findall("item"):
            items.append(
                {
                    "title": _text(item.find("title")),
                    "url": _text(item.find("link")),
                    "body": _text(item.find("description")),
                    "date": _text(item.find("pubDate")),
                    "source": source,
                }
            )

    return [item for item in items if item["title"] and item["url"]]


class RssFeedTool:
    """Fetches configured RSS/Atom feeds once per run and serves
    keyword-matched items as extra search candidates."""

    def __init__(self, settings: AppSettings):
        self._feeds = list(settings.search.rss_feeds)
        self._proxy = settings.search.proxy or settings.proxy
        self._cache: list[dict[str, str]] | None = None
        self._lock = asyncio.Lock()

    @property
    def has_feeds(self) -> bool:
        return bool(self._feeds)

    async def _fetch_all(self) -> list[dict[str, str]]:
        async with self._lock:
            if self._cache is not None:
                return self._cache
            items: list[dict[str, str]] = []
            if self._feeds:
                async with httpx.AsyncClient(
                    proxy=self._proxy or None,
                    timeout=20.0,
                    follow_redirects=True,
                ) as client:
                    responses = await asyncio.gather(
                        *(client.get(feed) for feed in self._feeds),
                        return_exceptions=True,
                    )
                for feed, response in zip(self._feeds, responses):
                    if isinstance(response, BaseException):
                        continue
                    if response.status_code != 200:
                        continue
                    items.extend(parse_feed(response.text))
            self._cache = items
            return items

    async def find_news(
        self,
        *,
        tokens: list[str],
        timelimit: SearchNewsTimeLimit,
        max_results: int,
    ) -> list[dict[str, Any]]:
        if not self._feeds or not tokens:
            return []
        items = await self._fetch_all()
        cutoff = datetime.now(timezone.utc) - timedelta(days=_TIMELIMIT_DAYS.get(timelimit, 1))
        normalized_tokens = [token.lower() for token in tokens if len(token) > 2]
        if not normalized_tokens:
            return []

        matched: list[dict[str, Any]] = []
        for item in items:
            published = _parse_date(item.get("date") or "")
            if published is not None and published < cutoff:
                continue
            haystack = f"{item.get('title', '')} {item.get('body', '')}".lower()
            if not any(token in haystack for token in normalized_tokens):
                continue
            matched.append(dict(item))
            if len(matched) >= max_results:
                break
        return matched


def create_rss_tool(settings: AppSettings) -> RssFeedTool:
    return RssFeedTool(settings)


__all__ = ["RssFeedTool", "create_rss_tool", "parse_feed"]
