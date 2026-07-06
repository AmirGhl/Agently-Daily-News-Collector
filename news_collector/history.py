from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


class NewsHistory:
    """Persistent record of already-published story URLs.

    Lets a daily run skip stories that appeared in earlier reports so
    consecutive briefings stay fresh instead of repeating yesterday's news.
    """

    def __init__(self, path: str | Path, *, retention_days: int = 30):
        self._path = Path(path)
        self._retention_days = max(retention_days, 1)
        self._entries: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        cutoff = (datetime.now() - timedelta(days=self._retention_days)).strftime("%Y-%m-%d")
        for url, entry in raw.items():
            if not isinstance(entry, dict):
                continue
            published_on = str(entry.get("date") or "")
            if published_on and published_on < cutoff:
                continue
            self._entries[str(url)] = {
                "date": published_on,
                "title": str(entry.get("title") or ""),
            }

    def is_seen(self, url: str) -> bool:
        return url.strip() in self._entries

    def mark_published(self, news_items: Iterable[dict[str, Any]], *, date: str) -> None:
        for news in news_items:
            url = str(news.get("url") or "").strip()
            if not url:
                continue
            self._entries[url] = {
                "date": date,
                "title": str(news.get("title") or ""),
            }

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def __len__(self) -> int:
        return len(self._entries)


__all__ = ["NewsHistory"]
