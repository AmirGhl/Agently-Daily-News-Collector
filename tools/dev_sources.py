from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from news_collector.config import SECURITY_SEVERITY_ORDER, AppSettings

USER_AGENT = "Agently-Daily-News-Collector/4 (personal news digest)"
GITHUB_REPO_URL_RE = re.compile(r"^https?://github\.com/([\w.-]+)/([\w.-]+)/?$")
_GITHUB_PATH_RE = re.compile(r"^https?://github\.com/([\w.-]+/[\w.-]+)")
_IMG_TAG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]+content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\']',
    re.IGNORECASE,
)


def _clean_image_url(url: str | None, *, base_url: str = "") -> str:
    """Normalize a scraped image URL; return '' when unusable."""
    from html import unescape

    candidate = unescape(str(url or "").strip())
    if not candidate or candidate.startswith("data:"):
        return ""
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    elif candidate.startswith("/") and base_url:
        parsed = urlparse(base_url)
        candidate = f"{parsed.scheme}://{parsed.netloc}{candidate}"
    if not candidate.startswith(("http://", "https://")):
        return ""
    return candidate


def github_social_image(url: str) -> str:
    """GitHub's OpenGraph card for a repo/release/issue URL — a rich social
    image (repo name, avatar, stars) served by GitHub itself, no API call."""
    match = _GITHUB_PATH_RE.match(str(url or "").strip())
    if match is None:
        return ""
    return f"https://opengraph.githubassets.com/agently/{match.group(1)}"


def _first_image_in_html(html_text: str, *, base_url: str = "") -> str:
    for match in _IMG_TAG_RE.finditer(html_text or ""):
        cleaned = _clean_image_url(match.group(1), base_url=base_url)
        if cleaned and not re.search(r"(pixel|spacer|blank|1x1|emoji|badge|shields\.io)", cleaned, re.IGNORECASE):
            return cleaned
    return ""


async def fetch_og_image(
    url: str,
    *,
    proxy: str | None = None,
    timeout: float = 10.0,
) -> str:
    """Fetch a page's og:image / twitter:image with a small bounded GET.
    Returns '' on any failure — images are progressive enhancement only."""
    github_image = github_social_image(url)
    if github_image:
        return github_image
    try:
        async with httpx.AsyncClient(
            proxy=proxy or None,
            timeout=timeout,
            follow_redirects=True,
            headers=_headers({"Accept": "text/html"}),
        ) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    return ""
                content_type = response.headers.get("content-type", "")
                if "html" not in content_type:
                    return ""
                head = b""
                async for chunk in response.aiter_bytes():
                    head += chunk
                    if len(head) >= 131072:  # meta og tags live in <head>
                        break
        text = head.decode("utf-8", errors="ignore")
        match = _OG_IMAGE_RE.search(text)
        if match:
            return _clean_image_url(match.group(1) or match.group(2), base_url=url)
    except Exception:
        pass
    return ""

CHANNELS = (
    "github_trending",
    "github_rising",
    "github_new",
    "github_releases",
    "github_advisories",
    "hackernews",
    "lobsters",
    "reddit",
    "devto",
    "product_hunt",
    "daily_dev",
    "extra_feeds",
)


def _headers(extra: dict[str, str] | None = None, *, github: bool = False) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    # An optional token lifts api.github.com rate limits (60/h -> 5000/h).
    # Only attach it to GitHub calls: leaking it to other hosts is unsafe and
    # makes reddit/product hunt reject the request outright.
    if github:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


class DevSourcesTool:
    """Aggregates developer-news channels (GitHub / HN / Reddit / Lobsters)
    into the same normalized item shape the search tool produces."""

    def __init__(self, settings: AppSettings, *, trends_path: "os.PathLike[str] | str | None" = None):
        self._config = settings.dev_pulse
        self._proxy = settings.search.proxy or settings.proxy
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()
        self._trends_path = trends_path
        self._log = logging.getLogger("agently_daily_news_collector")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            proxy=self._proxy or None,
            timeout=25.0,
            follow_redirects=True,
            headers=_headers(),
        )

    async def fetch_channels(
        self,
        channels: list[str],
        *,
        limit_per_channel: int = 10,
    ) -> list[dict[str, Any]]:
        fetched = await asyncio.gather(
            *(self._fetch_channel(str(channel)) for channel in channels),
            return_exceptions=True,
        )
        results: list[dict[str, Any]] = []
        for channel, items in zip(channels, fetched):
            if isinstance(items, BaseException):
                self._log.info("[Dev Channel] %s: failed (%s)", channel, type(items).__name__)
                continue
            self._log.info("[Dev Channel] %s: %d items", channel, len(items))
            results.extend(items[:limit_per_channel])
        return results

    async def _fetch_channel(self, channel: str) -> list[dict[str, Any]]:
        async with self._lock:
            if channel in self._cache:
                return self._cache[channel]
        if channel == "github_trending":
            items = await self._github_trending()
        elif channel == "github_rising":
            items = await self._github_rising()
        elif channel == "github_new":
            items = await self._github_new_hot()
        elif channel == "github_releases":
            items = await self._github_releases()
        elif channel == "github_advisories":
            items = await self._github_advisories()
        elif channel == "hackernews":
            items = await self._hackernews()
        elif channel == "lobsters":
            items = await self._lobsters()
        elif channel == "reddit":
            items = await self._reddit()
        elif channel == "devto":
            items = await self._devto()
        elif channel == "product_hunt":
            items = await self._product_hunt()
        elif channel == "daily_dev":
            items = await self._daily_dev()
        elif channel == "extra_feeds":
            items = await self._extra_feeds()
        else:
            items = []
        async with self._lock:
            self._cache[channel] = items
        return items

    # ---- GitHub -----------------------------------------------------------

    async def _github_trending(self) -> list[dict[str, Any]]:
        url = "https://github.com/trending"
        params = {"since": "daily"}
        if self._config.github_language:
            url += f"/{self._config.github_language}"
        async with self._client() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items: list[dict[str, Any]] = []
        for row in soup.select("article.Box-row"):
            anchor = row.select_one("h2 a")
            if anchor is None or not anchor.get("href"):
                continue
            repo_path = str(anchor["href"]).strip("/")
            description_el = row.select_one("p")
            description = description_el.get_text(" ", strip=True) if description_el else ""
            stars_today = ""
            stars_today_el = row.select_one("span.d-inline-block.float-sm-right")
            if stars_today_el:
                stars_today = stars_today_el.get_text(" ", strip=True)
            language_el = row.select_one('[itemprop="programmingLanguage"]')
            language = language_el.get_text(strip=True) if language_el else ""
            brief_parts = [part for part in (description, language, stars_today) if part]
            repo_url = f"https://github.com/{repo_path}"
            items.append(
                {
                    "title": repo_path,
                    "url": repo_url,
                    "body": " · ".join(brief_parts),
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "source": "GitHub Trending",
                    "image": github_social_image(repo_url),
                }
            )
        self._annotate_trend_streaks(items)
        return items

    def _annotate_trend_streaks(self, items: list[dict[str, Any]]) -> None:
        """Track how many consecutive days a repo has been on the trending
        page and stamp streaks of 2+ days onto the item brief."""
        if not self._trends_path:
            return
        import json
        from pathlib import Path

        path = Path(self._trends_path)
        trends: dict[str, dict[str, Any]] = {}
        try:
            if path.exists():
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    trends = raw
        except (OSError, ValueError):
            trends = {}

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stale_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
        trends = {
            url: entry
            for url, entry in trends.items()
            if isinstance(entry, dict) and str(entry.get("last_seen") or "") >= stale_cutoff
        }
        for item in items:
            url = item["url"]
            entry = trends.get(url)
            if entry is None:
                entry = {"first_seen": today, "last_seen": today, "days": 1}
            elif entry.get("last_seen") != today:
                yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
                entry["days"] = (entry.get("days", 0) + 1) if entry.get("last_seen") == yesterday else 1
                entry["last_seen"] = today
            trends[url] = entry
            days = int(entry.get("days") or 1)
            if days >= 2:
                item["body"] = f"{item['body']} · 🔥 trending {days} days in a row".strip(" ·")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(trends, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass

    async def _github_rising(self) -> list[dict[str, Any]]:
        """Repos gaining stars fast right now, independent of the GitHub
        trending page. Primary: OSS Insight's trends API (star events over the
        past 24h). Fallback: the weekly trending page, which catches repos
        that accumulated stars over ~48h without ever hitting daily trending."""
        try:
            items = await self._github_rising_ossinsight()
            if items:
                return items
        except Exception:
            pass
        return await self._github_trending_weekly()

    async def _github_rising_ossinsight(self) -> list[dict[str, Any]]:
        params = {"period": "past_24_hours", "language": "All"}
        if self._config.github_language:
            params["language"] = self._config.github_language
        async with self._client() as client:
            response = await client.get("https://api.ossinsight.io/v1/trends/repos/", params=params)
            response.raise_for_status()
        rows = ((response.json().get("data") or {}).get("rows")) or []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        items: list[dict[str, Any]] = []
        for row in rows:
            repo_name = str(row.get("repo_name") or "")
            stars_gained = int(float(row.get("stars") or 0))
            if not repo_name or stars_gained < self._config.min_rising_stars:
                continue
            brief_parts = [
                str(row.get("description") or ""),
                str(row.get("primary_language") or ""),
                f"★ +{stars_gained} stars in 24h",
                f"{int(float(row.get('total_score') or 0))} total" if row.get("total_score") else "",
            ]
            repo_url = f"https://github.com/{repo_name}"
            items.append(
                {
                    "title": repo_name,
                    "url": repo_url,
                    "body": " · ".join(part for part in brief_parts if part),
                    "date": today,
                    "source": "GitHub Rising",
                    "image": github_social_image(repo_url),
                }
            )
        return items

    async def _github_trending_weekly(self) -> list[dict[str, Any]]:
        url = "https://github.com/trending"
        if self._config.github_language:
            url += f"/{self._config.github_language}"
        async with self._client() as client:
            response = await client.get(url, params={"since": "weekly"})
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        items: list[dict[str, Any]] = []
        for row in soup.select("article.Box-row"):
            anchor = row.select_one("h2 a")
            if anchor is None or not anchor.get("href"):
                continue
            repo_path = str(anchor["href"]).strip("/")
            description_el = row.select_one("p")
            description = description_el.get_text(" ", strip=True) if description_el else ""
            stars_week_el = row.select_one("span.d-inline-block.float-sm-right")
            stars_week = stars_week_el.get_text(" ", strip=True) if stars_week_el else ""
            language_el = row.select_one('[itemprop="programmingLanguage"]')
            language = language_el.get_text(strip=True) if language_el else ""
            brief_parts = [description, language, stars_week]
            repo_url = f"https://github.com/{repo_path}"
            items.append(
                {
                    "title": repo_path,
                    "url": repo_url,
                    "body": " · ".join(part for part in brief_parts if part),
                    "date": today,
                    "source": "GitHub Rising",
                    "image": github_social_image(repo_url),
                }
            )
        return items

    async def _github_new_hot(self) -> list[dict[str, Any]]:
        created_after = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        query = f"created:>{created_after} stars:>50"
        if self._config.github_language:
            query += f" language:{self._config.github_language}"
        async with self._client() as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": 15},
                headers=_headers({"Accept": "application/vnd.github+json"}, github=True),
            )
            response.raise_for_status()
        items: list[dict[str, Any]] = []
        for repo in response.json().get("items", []):
            description = str(repo.get("description") or "")
            brief_parts = [
                description,
                str(repo.get("language") or ""),
                f"★ {repo.get('stargazers_count', 0)} (new repo)",
            ]
            repo_html_url = str(repo.get("html_url") or "")
            items.append(
                {
                    "title": str(repo.get("full_name") or ""),
                    "url": repo_html_url,
                    "body": " · ".join(part for part in brief_parts if part),
                    "date": str(repo.get("created_at") or "")[:10],
                    "source": "GitHub New & Rising",
                    "image": github_social_image(repo_html_url),
                }
            )
        return items

    async def _github_releases(self) -> list[dict[str, Any]]:
        """Fresh releases from the watched repos, changelog included inline."""
        if not self._config.watch_repos:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._config.release_window_days)
        items: list[dict[str, Any]] = []
        async with self._client() as client:
            responses = await asyncio.gather(
                *(
                    client.get(
                        f"https://api.github.com/repos/{repo}/releases",
                        params={"per_page": 3},
                        headers=_headers({"Accept": "application/vnd.github+json"}, github=True),
                    )
                    for repo in self._config.watch_repos
                ),
                return_exceptions=True,
            )
        for repo, response in zip(self._config.watch_repos, responses):
            if isinstance(response, BaseException) or response.status_code != 200:
                continue
            for release in response.json():
                if release.get("draft") or release.get("prerelease"):
                    continue
                published = str(release.get("published_at") or "")
                try:
                    published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if published_at < cutoff:
                    continue
                tag = str(release.get("tag_name") or release.get("name") or "")
                notes = str(release.get("body") or "").strip()
                items.append(
                    {
                        "title": f"{repo} {tag}".strip(),
                        "url": str(release.get("html_url") or f"https://github.com/{repo}/releases"),
                        "body": f"New release of {repo} · published {published[:10]}",
                        "date": published[:10],
                        "source": "GitHub Releases",
                        "kind": "release",
                        "image": github_social_image(f"https://github.com/{repo}"),
                        "content": f"Repository: {repo}\nRelease: {tag}\nPublished: {published[:10]}\n\nRelease notes:\n{notes}"[:12000],
                    }
                )
        items.sort(key=lambda item: item["date"], reverse=True)
        return items

    async def _github_advisories(self) -> list[dict[str, Any]]:
        """Recent high-severity security advisories for configured ecosystems."""
        if not self._config.security_ecosystems:
            return []
        min_index = SECURITY_SEVERITY_ORDER.index(self._config.security_min_severity)
        allowed_severities = set(SECURITY_SEVERITY_ORDER[min_index:])
        wanted_ecosystems = {eco.lower() for eco in self._config.security_ecosystems}
        cutoff = datetime.now(timezone.utc) - timedelta(days=3)
        async with self._client() as client:
            response = await client.get(
                "https://api.github.com/advisories",
                params={"per_page": 40, "sort": "published", "direction": "desc"},
                headers=_headers({"Accept": "application/vnd.github+json"}, github=True),
            )
            response.raise_for_status()
        items: list[dict[str, Any]] = []
        for advisory in response.json():
            severity = str(advisory.get("severity") or "").lower()
            if severity not in allowed_severities:
                continue
            published = str(advisory.get("published_at") or "")
            try:
                published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                continue
            if published_at < cutoff:
                continue
            packages = []
            for vulnerability in advisory.get("vulnerabilities") or []:
                package = (vulnerability.get("package") or {})
                ecosystem = str(package.get("ecosystem") or "").lower()
                if ecosystem in wanted_ecosystems:
                    ranges = str(vulnerability.get("vulnerable_version_range") or "")
                    packages.append(f"{package.get('name')} ({ecosystem}) {ranges}".strip())
            if not packages:
                continue
            summary = str(advisory.get("summary") or "")
            description = str(advisory.get("description") or "").strip()
            items.append(
                {
                    "title": f"[{severity.upper()}] {summary}",
                    "url": str(advisory.get("html_url") or ""),
                    "body": f"{severity} severity · affects {', '.join(packages[:3])}",
                    "date": published[:10],
                    "source": "GitHub Security Advisories",
                    "kind": "advisory",
                    "content": (
                        f"Advisory: {summary}\nSeverity: {severity}\n"
                        f"Affected packages: {'; '.join(packages)}\n"
                        f"CVE: {advisory.get('cve_id') or '-'}\nPublished: {published[:10]}\n\n"
                        f"{description}"
                    )[:12000],
                }
            )
        return items

    # ---- Hacker News / Lobsters / Reddit -----------------------------------

    async def _hackernews(self) -> list[dict[str, Any]]:
        # Algolia is the richest HN API but is unreachable from some networks;
        # hnrss.org serves the same stories as RSS; the official Firebase API
        # is the last resort (one request per story, but it always answers).
        for fetcher in (
            self._hackernews_algolia,
            self._hackernews_rss,
            self._hackernews_firebase,
        ):
            try:
                items = await fetcher()
                if items:
                    return items
            except Exception:
                continue
        return []

    async def _hackernews_algolia(self) -> list[dict[str, Any]]:
        created_after = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        async with self._client() as client:
            response = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "tags": "story",
                    "numericFilters": f"points>{self._config.min_hn_points},created_at_i>{created_after}",
                    "hitsPerPage": 30,
                },
            )
            response.raise_for_status()
        items: list[tuple[int, dict[str, Any]]] = []
        for hit in response.json().get("hits", []):
            url = str(hit.get("url") or "")
            if not url:
                object_id = hit.get("objectID")
                url = f"https://news.ycombinator.com/item?id={object_id}" if object_id else ""
            points = int(hit.get("points") or 0)
            items.append(
                (
                    points,
                    {
                        "title": str(hit.get("title") or ""),
                        "url": url,
                        "body": f"{points} points · {hit.get('num_comments', 0)} comments on Hacker News",
                        "date": str(hit.get("created_at") or "")[:10],
                        "source": "Hacker News",
                    },
                )
            )
        items.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in items]

    async def _hackernews_rss(self) -> list[dict[str, Any]]:
        from .rss import parse_feed

        async with self._client() as client:
            response = await client.get(
                "https://hnrss.org/best",
                params={"points": self._config.min_hn_points, "count": 30},
            )
            response.raise_for_status()
        items: list[dict[str, Any]] = []
        for entry in parse_feed(response.text):
            body = "Hacker News front page story"
            match = re.search(r"Points:\s*(\d+)", entry.get("body") or "")
            comments_match = re.search(r"Comments:\s*(\d+)", entry.get("body") or "")
            if match:
                body = f"{match.group(1)} points"
                if comments_match:
                    body += f" · {comments_match.group(1)} comments"
                body += " on Hacker News"
            items.append(
                {
                    "title": entry["title"],
                    "url": entry["url"],
                    "body": body,
                    "date": entry.get("date") or "",
                    "source": "Hacker News",
                }
            )
        return items

    async def _hackernews_firebase(self) -> list[dict[str, Any]]:
        async with self._client() as client:
            response = await client.get("https://hacker-news.firebaseio.com/v0/beststories.json")
            response.raise_for_status()
            ids = [int(story_id) for story_id in (response.json() or [])[:40]]
            stories = await asyncio.gather(
                *(
                    client.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                    for story_id in ids
                ),
                return_exceptions=True,
            )
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        items: list[tuple[int, dict[str, Any]]] = []
        for story_response in stories:
            if isinstance(story_response, BaseException) or story_response.status_code != 200:
                continue
            story = story_response.json() or {}
            points = int(story.get("score") or 0)
            if points < self._config.min_hn_points:
                continue
            posted = datetime.fromtimestamp(float(story.get("time") or 0), tz=timezone.utc)
            if posted < cutoff:
                continue
            story_id = story.get("id")
            url = str(
                story.get("url")
                or (f"https://news.ycombinator.com/item?id={story_id}" if story_id else "")
            )
            items.append(
                (
                    points,
                    {
                        "title": str(story.get("title") or ""),
                        "url": url,
                        "body": f"{points} points · {story.get('descendants', 0)} comments on Hacker News",
                        "date": posted.strftime("%Y-%m-%d"),
                        "source": "Hacker News",
                    },
                )
            )
        items.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in items]

    async def _lobsters(self) -> list[dict[str, Any]]:
        async with self._client() as client:
            response = await client.get("https://lobste.rs/hottest.json")
            response.raise_for_status()
        items: list[dict[str, Any]] = []
        for story in response.json():
            if int(story.get("score") or 0) < self._config.min_lobsters_score:
                continue
            tags = ", ".join(story.get("tags") or [])
            items.append(
                {
                    "title": str(story.get("title") or ""),
                    "url": str(story.get("url") or story.get("comments_url") or ""),
                    "body": f"{story.get('score', 0)} points on Lobsters" + (f" · {tags}" if tags else ""),
                    "date": str(story.get("created_at") or "")[:10],
                    "source": "Lobsters",
                }
            )
        return items

    async def _reddit(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        async with self._client() as client:
            for subreddit in self._config.reddit_subreddits:
                try:
                    items.extend(await self._reddit_json(client, subreddit))
                except Exception:
                    # reddit.com's JSON API 403s many networks; the
                    # old.reddit.com RSS mirror usually still answers — but
                    # only from a fresh client: the 403 plants a block cookie
                    # on .reddit.com that poisons the shared client.
                    try:
                        items.extend(await self._reddit_rss(subreddit))
                    except Exception:
                        continue
        items.sort(
            key=lambda item: int(re.search(r"(\d+) upvotes", item["body"]).group(1))
            if re.search(r"(\d+) upvotes", item["body"])
            else 0,
            reverse=True,
        )
        return items

    async def _reddit_json(self, client: httpx.AsyncClient, subreddit: str) -> list[dict[str, Any]]:
        response = await client.get(
            f"https://www.reddit.com/r/{subreddit}/top.json",
            params={"t": "day", "limit": 20},
        )
        response.raise_for_status()
        items: list[dict[str, Any]] = []
        for child in response.json().get("data", {}).get("children", []):
                    post = child.get("data") or {}
                    score = int(post.get("score") or 0)
                    if score < self._config.min_reddit_score:
                        continue
                    permalink = f"https://www.reddit.com{post.get('permalink', '')}"
                    external_url = str(post.get("url") or "")
                    is_self_post = bool(post.get("is_self"))
                    url = permalink if is_self_post else (external_url or permalink)
                    selftext = str(post.get("selftext") or "").strip()
                    brief = selftext[:280] if selftext else ""
                    meta = f"{score} upvotes · {post.get('num_comments', 0)} comments on r/{subreddit}"
                    image = ""
                    try:
                        preview_images = ((post.get("preview") or {}).get("images")) or []
                        if preview_images:
                            image = _clean_image_url(
                                ((preview_images[0].get("source")) or {}).get("url")
                            )
                    except (AttributeError, IndexError, TypeError):
                        image = ""
                    if not image:
                        thumbnail = str(post.get("thumbnail") or "")
                        if thumbnail.startswith("http"):
                            image = _clean_image_url(thumbnail)
                    item: dict[str, Any] = {
                        "title": str(post.get("title") or ""),
                        "url": url,
                        "body": f"{brief} {meta}".strip(),
                        "date": datetime.fromtimestamp(
                            float(post.get("created_utc") or 0), tz=timezone.utc
                        ).strftime("%Y-%m-%d"),
                        "source": f"Reddit r/{subreddit}",
                    }
                    if image:
                        item["image"] = image
                    # Self posts carry their full text: no need to browse
                    # (reddit.com often blocks scrapers anyway).
                    if is_self_post and len(selftext) > 200:
                        item["content"] = f"Reddit post ({meta}):\n\n{selftext}"[:12000]
                    items.append(item)
        items.sort(
            key=lambda item: int(re.search(r"(\d+) upvotes", item["body"]).group(1))
            if re.search(r"(\d+) upvotes", item["body"])
            else 0,
            reverse=True,
        )
        return items


    async def _reddit_rss(self, subreddit: str) -> list[dict[str, Any]]:
        from .rss import parse_feed

        # No `limit` param here — old.reddit's blocker 403s the RSS route
        # when it is present; `t=day` alone passes. Pace requests to stay
        # under the anonymous rate limit.
        await asyncio.sleep(1.2)
        async with self._client() as client:
            response = await client.get(
                f"https://old.reddit.com/r/{subreddit}/top/.rss",
                params={"t": "day"},
            )
            response.raise_for_status()
        items: list[dict[str, Any]] = []
        for entry in parse_feed(response.text):
            text = re.sub(r"<[^>]+>", " ", entry.get("body") or "")
            text = re.sub(r"submitted by\s+/u/\S+.*$", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\[link\]|\[comments\]", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            items.append(
                {
                    "title": entry["title"],
                    "url": entry["url"],
                    "body": f"{text[:240]} · top today on r/{subreddit}".strip(" ·"),
                    "date": (entry.get("date") or "")[:10],
                    "source": f"Reddit r/{subreddit}",
                }
            )
        return items

    async def _devto(self) -> list[dict[str, Any]]:
        async with self._client() as client:
            response = await client.get(
                "https://dev.to/api/articles",
                params={"top": 3, "per_page": 30},
            )
            response.raise_for_status()
        items: list[dict[str, Any]] = []
        for article in response.json():
            reactions = int(article.get("positive_reactions_count") or 0)
            if reactions < self._config.min_devto_reactions:
                continue
            tags = ", ".join(article.get("tag_list") or [])
            item = {
                "title": str(article.get("title") or ""),
                "url": str(article.get("url") or ""),
                "body": f"{str(article.get('description') or '').strip()} "
                f"· {reactions} reactions on dev.to"
                + (f" · {tags}" if tags else ""),
                "date": str(article.get("published_at") or "")[:10],
                "source": "dev.to",
            }
            image = _clean_image_url(
                article.get("cover_image") or article.get("social_image")
            )
            if image:
                item["image"] = image
            items.append(item)
        items.sort(key=lambda item: item["date"], reverse=True)
        return items

    # ---- Product Hunt / daily.dev / custom feeds ----------------------------

    async def _product_hunt(self) -> list[dict[str, Any]]:
        """Today's Product Hunt front page via its public Atom feed."""
        from .rss import parse_feed

        async with self._client() as client:
            response = await client.get("https://www.producthunt.com/feed")
            response.raise_for_status()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        items: list[dict[str, Any]] = []
        for entry in parse_feed(response.text):
            date = (entry.get("date") or "")[:10]
            if date and date < cutoff:
                continue
            raw_body = entry.get("body") or ""
            text = re.sub(r"<[^>]+>", " ", raw_body)
            text = re.sub(r"\s+", " ", text).strip()
            item = {
                "title": entry["title"],
                "url": entry["url"],
                "body": f"{text[:240]} · launched on Product Hunt".strip(" ·"),
                "date": date,
                "source": "Product Hunt",
            }
            image = _first_image_in_html(raw_body, base_url=entry["url"])
            if image:
                item["image"] = image
            items.append(item)
        return items

    async def _daily_dev(self) -> list[dict[str, Any]]:
        """daily.dev most-upvoted-this-week via its public GraphQL endpoint.
        (The anonymous POPULARITY feed serves stale content; mostUpvotedFeed
        with a period is both fresh and quality-ranked.)"""
        async with self._client() as client:
            response = await client.post(
                "https://api.daily.dev/graphql",
                json={
                    "query": _DAILY_DEV_QUERY,
                    "variables": {"first": 40, "period": 7},
                },
            )
            response.raise_for_status()
        edges = (((response.json().get("data") or {}).get("page") or {}).get("edges")) or []
        cutoff = datetime.now(timezone.utc) - timedelta(days=8)
        scored: list[tuple[int, dict[str, Any]]] = []
        for edge in edges:
            node = edge.get("node") or {}
            upvotes = int(node.get("numUpvotes") or 0)
            if upvotes < self._config.min_dailydev_upvotes:
                continue
            created = str(node.get("createdAt") or "")
            try:
                created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                continue
            if created_at < cutoff:
                continue
            tags = ", ".join(node.get("tags") or [])
            scored.append(
                (
                    upvotes,
                    {
                        "title": str(node.get("title") or ""),
                        "url": str(node.get("url") or node.get("permalink") or ""),
                        "body": f"{upvotes} upvotes · {node.get('numComments', 0)} comments on daily.dev"
                        + (f" · {tags}" if tags else ""),
                        "date": created[:10],
                        "source": "daily.dev",
                    },
                )
            )
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored]

    async def _extra_feeds(self) -> list[dict[str, Any]]:
        """User-configured RSS/Atom feeds (DEV_PULSE.extra_feeds) — the bridge
        for anything without a friendly API (X/Twitter via RSSHub, blogs, …)."""
        feeds = self._config.extra_feeds
        if not feeds:
            return []
        from .rss import parse_feed

        async with self._client() as client:
            responses = await asyncio.gather(
                *(client.get(feed) for feed in feeds), return_exceptions=True
            )
        items: list[dict[str, Any]] = []
        for feed, response in zip(feeds, responses):
            if isinstance(response, BaseException) or response.status_code != 200:
                continue
            host = urlparse(feed).netloc or feed
            for entry in parse_feed(response.text)[:10]:
                raw_body = entry.get("body") or ""
                text = re.sub(r"<[^>]+>", " ", raw_body)
                text = re.sub(r"\s+", " ", text).strip()
                item = {
                    "title": entry["title"],
                    "url": entry["url"],
                    "body": f"{text[:240]} · via {host}".strip(" ·"),
                    "date": (entry.get("date") or "")[:10],
                    "source": host,
                }
                image = _first_image_in_html(raw_body, base_url=entry["url"])
                if image:
                    item["image"] = image
                items.append(item)
        return items


_DAILY_DEV_QUERY = (
    "query MostUpvotedFeed($first: Int, $period: Int) {"
    " page: mostUpvotedFeed(first: $first, period: $period) {"
    " edges { node { title permalink url createdAt numUpvotes numComments tags } } } }"
)


async def fetch_github_repo_content(
    url: str,
    *,
    proxy: str | None = None,
    max_length: int = 12000,
) -> str:
    """README + metadata for a GitHub repo URL, as markdown for the LLM."""
    match = GITHUB_REPO_URL_RE.match(url.strip())
    if match is None:
        return ""
    owner, repo = match.group(1), match.group(2)

    meta_lines: list[str] = []
    readme = ""
    async with httpx.AsyncClient(
        proxy=proxy or None,
        timeout=25.0,
        follow_redirects=True,
        headers=_headers(),
    ) as client:
        try:
            meta_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=_headers({"Accept": "application/vnd.github+json"}, github=True),
            )
            if meta_response.status_code == 200:
                meta = meta_response.json()
                meta_lines = [
                    f"Repository: {meta.get('full_name')}",
                    f"Description: {meta.get('description') or '-'}",
                    f"Stars: {meta.get('stargazers_count', 0)} · Forks: {meta.get('forks_count', 0)}",
                    f"Language: {meta.get('language') or '-'} · License: {(meta.get('license') or {}).get('spdx_id', '-')}",
                    f"Created: {str(meta.get('created_at') or '')[:10]} · Last push: {str(meta.get('pushed_at') or '')[:10]}",
                ]
        except Exception:
            pass
        try:
            readme_response = await client.get(
                f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
            )
            if readme_response.status_code == 200:
                readme = readme_response.text
        except Exception:
            pass
        if not readme:
            try:
                readme_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/readme",
                    headers=_headers({"Accept": "application/vnd.github.raw+json"}, github=True),
                )
                if readme_response.status_code == 200:
                    readme = readme_response.text
            except Exception:
                pass

    if not meta_lines and not readme:
        return ""
    content = "\n".join(meta_lines) + "\n\n---\n\n" + readme
    return content.strip()[:max_length]


def create_dev_sources_tool(
    settings: AppSettings,
    *,
    root_dir: "os.PathLike[str] | str | None" = None,
) -> DevSourcesTool:
    trends_path = None
    if root_dir is not None:
        from pathlib import Path

        trends_path = Path(root_dir) / settings.output.directory / ".trends.json"
    return DevSourcesTool(settings, trends_path=trends_path)


__all__ = [
    "CHANNELS",
    "DevSourcesTool",
    "GITHUB_REPO_URL_RE",
    "create_dev_sources_tool",
    "fetch_github_repo_content",
    "fetch_og_image",
    "github_social_image",
]
