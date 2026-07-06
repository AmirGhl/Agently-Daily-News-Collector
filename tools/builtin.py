from __future__ import annotations

from typing import Any

import httpx
from agently.builtins.tools import Browse, Search
from ddgs.exceptions import DDGSException

from news_collector.config import AppSettings, SearchNewsTimeLimit

from .base import BrowseToolProtocol, SearchToolProtocol
from .content_quality import is_invalid_browse_content

JINA_READER_PREFIX = "https://r.jina.ai/"


class AgentlyBuiltinSearchTool(SearchToolProtocol):
    def __init__(self, settings: AppSettings):
        search_proxy = settings.search.proxy or settings.proxy
        self._tool = Search(
            proxy=search_proxy,
            region=settings.search.region,
            backend=settings.search.backend,
        )
        # Individual backends get rate-limited intermittently; "auto" rotates
        # providers, so keep it as a second attempt when the primary is dry.
        self._fallback_tool = (
            Search(proxy=search_proxy, region=settings.search.region, backend="auto")
            if settings.search.backend != "auto"
            else None
        )

    async def search_news(
        self,
        *,
        query: str,
        timelimit: SearchNewsTimeLimit,
        max_results: int,
    ) -> list[dict[str, Any]]:
        results = await self._search_with(
            self._tool,
            query=query,
            timelimit=timelimit,
            max_results=max_results,
        )
        if not results and self._fallback_tool is not None:
            results = await self._search_with(
                self._fallback_tool,
                query=query,
                timelimit=timelimit,
                max_results=max_results,
            )
        return results

    @staticmethod
    async def _search_with(
        tool: Search,
        *,
        query: str,
        timelimit: SearchNewsTimeLimit,
        max_results: int,
    ) -> list[dict[str, Any]]:
        try:
            results = await tool.search_news(
                query=query,
                timelimit=timelimit,
                max_results=max_results,
            )
        except DDGSException as exc:
            if "No results found" in str(exc):
                return []
            raise
        return results if isinstance(results, list) else []


class AgentlyBuiltinBrowseTool(BrowseToolProtocol):
    def __init__(self, settings: AppSettings):
        self._browse_settings = settings.browse
        self._proxy = settings.browse.proxy or settings.proxy
        self._tool = Browse(
            proxy=self._proxy,
            enable_pyautogui=False,
            enable_playwright=settings.browse.enable_playwright,
            enable_bs4=True,
            response_mode=settings.browse.response_mode,
            max_content_length=settings.browse.max_content_length,
            min_content_length=settings.browse.min_content_length,
            playwright_headless=settings.browse.playwright_headless,
        )

    async def browse(self, url: str) -> str:
        result = str(await self._tool.browse(url) or "")
        if self._is_usable(result) or not self._browse_settings.enable_jina_fallback:
            return result
        fallback = await self._browse_via_jina_reader(url)
        return fallback if self._is_usable(fallback) else result

    def _is_usable(self, content: str) -> bool:
        stripped = content.strip()
        if len(stripped) < self._browse_settings.min_content_length:
            return False
        return not is_invalid_browse_content(stripped)

    async def _browse_via_jina_reader(self, url: str) -> str:
        # Jina Reader returns a clean markdown rendering of pages that block
        # plain HTTP scraping (bot walls, JS-only pages). No API key needed.
        try:
            async with httpx.AsyncClient(
                proxy=self._proxy or None,
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    JINA_READER_PREFIX + url,
                    headers={"X-Return-Format": "markdown"},
                )
                response.raise_for_status()
        except Exception:
            return ""
        return response.text.strip()[: self._browse_settings.max_content_length]


def create_search_tool(settings: AppSettings) -> SearchToolProtocol:
    return AgentlyBuiltinSearchTool(settings)


def create_browse_tool(settings: AppSettings) -> BrowseToolProtocol:
    return AgentlyBuiltinBrowseTool(settings)
