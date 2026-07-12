from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from .config import AppSettings


@dataclass
class ExportConfig:
    notion_token: str = ""
    notion_parent_page_id: str = ""
    obsidian_vault_path: str = ""
    enabled: bool = False


def get_export_config(settings: AppSettings) -> ExportConfig:
    """Build export config from settings and environment."""
    return ExportConfig(
        notion_token=os.getenv("NOTION_TOKEN", ""),
        notion_parent_page_id=os.getenv("NOTION_PARENT_PAGE_ID", ""),
        obsidian_vault_path=os.getenv("OBSIDIAN_VAULT_PATH", ""),
        enabled=bool(os.getenv("EXPORT_ENABLED", "false").lower() == "true"),
    )


async def export_to_notion(
    report: dict[str, Any],
    config: ExportConfig,
    logger: logging.Logger,
) -> bool:
    """Export report to Notion as a new page."""
    if not config.notion_token or not config.notion_parent_page_id:
        logger.warning("[Notion Export] Missing token or parent page ID")
        return False

    try:
        # Build Notion blocks from report
        blocks = build_notion_blocks(report)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create page
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {config.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                json={
                    "parent": {"page_id": config.notion_parent_page_id},
                    "properties": {
                        "title": {
                            "title": [{"text": {"content": report.get("report_title", "Daily News")}}]
                        }
                    },
                    "children": blocks,
                },
            )
            response.raise_for_status()
            logger.info("[Notion Export] Page created successfully")
            return True
    except Exception as exc:
        logger.warning("[Notion Export Failed] %s", exc)
        return False


def build_notion_blocks(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert report to Notion block structure."""
    blocks = []

    # TL;DR section
    tldr = report.get("tldr") or []
    if tldr:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📋 Key Takeaways"}}]}
        })
        for item in tldr:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": str(item)}}]
                }
            })

    # Columns
    for column in report.get("columns") or []:
        if not isinstance(column, dict):
            continue
        title = column.get("title", "")
        prologue = column.get("prologue", "")
        news_list = column.get("news_list") or []

        blocks.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {"rich_text": [{"type": "text", "text": {"content": title}}]}
        })
        if prologue:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": prologue}}]}
            })

        for news in news_list:
            if not isinstance(news, dict):
                continue
            news_title = news.get("title", "")
            url = news.get("url", "")
            summary = news.get("summary", "")
            source = news.get("source", "")

            # Title with link
            if url:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": news_title, "link": {"url": url}}
                        }]
                    }
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": news_title}}]}
                })

            meta_parts = []
            if source:
                meta_parts.append(f"Source: {source}")
            if news.get("date"):
                meta_parts.append(news.get("date")[:10])
            if meta_parts:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": " · ".join(meta_parts), "annotations": {"color": "gray"}}]}}
                })

            if summary:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]}
                })

    return blocks


async def export_to_obsidian(
    report: dict[str, Any],
    config: ExportConfig,
    logger: logging.Logger,
) -> bool:
    """Export report as Markdown file to Obsidian vault."""
    if not config.obsidian_vault_path:
        logger.warning("[Obsidian Export] Vault path not configured")
        return False

    vault_path = Path(config.obsidian_vault_path).expanduser()
    if not vault_path.exists():
        logger.warning("[Obsidian Export] Vault path does not exist: %s", vault_path)
        return False

    try:
        # Generate markdown content
        markdown = render_obsidian_markdown(report)
        
        # Create filename with date
        date_str = datetime.now().strftime("%Y-%m-%d")
        title = report.get("report_title", "daily-news").replace("/", "-")
        safe_title = re.sub(r"[^\w\- ]", "", title).strip()
        filename = f"{date_str}-{safe_title}.md"
        
        file_path = vault_path / filename
        
        # Write file
        file_path.write_text(markdown, encoding="utf-8")
        logger.info("[Obsidian Export] Saved to %s", file_path)
        return True
    except Exception as exc:
        logger.warning("[Obsidian Export Failed] %s", exc)
        return False


def render_obsidian_markdown(report: dict[str, Any]) -> str:
    """Render report as Obsidian-flavored Markdown with frontmatter."""
    lines = []
    
    # Frontmatter
    lines.append("---")
    lines.append(f"title: \"{report.get('report_title', 'Daily News')}\"")
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"topic: \"{report.get('topic', '')}\"")
    lines.append(f"language: \"{report.get('language', 'English')}\"")
    lines.append(f"model: \"{report.get('model', '')}\"")
    lines.append("tags: [daily-news, auto-generated]")
    lines.append("---")
    lines.append("")

    # TL;DR
    tldr = report.get("tldr") or []
    if tldr:
        lines.append("## 📋 Key Takeaways")
        lines.append("")
        for item in tldr:
            lines.append(f"- {item}")
        lines.append("")

    # Columns
    for column in report.get("columns") or []:
        if not isinstance(column, dict):
            continue
        title = column.get("title", "")
        prologue = column.get("prologue", "")
        news_list = column.get("news_list") or []

        lines.append(f"# {title}")
        lines.append("")
        if prologue:
            lines.append(prologue)
            lines.append("")

        for news in news_list:
            if not isinstance(news, dict):
                continue
            news_title = news.get("title", "")
            url = news.get("url", "")
            summary = news.get("summary", "")
            source = news.get("source", "")
            date = news.get("date", "")[:10]

            lines.append(f"## {news_title}")
            lines.append("")
            
            meta = []
            if source:
                meta.append(f"Source: {source}")
            if date:
                meta.append(f"Date: {date}")
            if meta:
                lines.append(f"*{' · '.join(meta)}*")
                lines.append("")

            if summary:
                lines.append(summary)
                lines.append("")

            if url:
                lines.append(f"[Read more]({url})")
                lines.append("")

    return "\n".join(lines)


# ============================================================================
# RAG Chat over Archive
# ============================================================================

@dataclass
class RAGConfig:
    vector_db_path: str = "outputs/.vector_db"
    top_k: int = 5
    model: str = "text-embedding-3-small"


class RAGChat:
    """Retrieval-Augmented Generation chat over report archive."""
    
    def __init__(self, settings: AppSettings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.config = RAGConfig()
        self._index_built = False
        self._vector_store = None

    def _ensure_vector_store(self):
        """Lazy-load vector store."""
        if self._index_built:
            return
        try:
            # Try to use sqlite-vec or chroma if available
            import sqlite3
            import sqlite_vec
            db_path = Path(self.settings.output.directory) / self.config.vector_db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(db_path))
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            self._init_schema()
            self._index_built = True
        except ImportError:
            # Fallback to simple text search
            self._index_built = True
            self._conn = None

    def _init_schema(self):
        """Initialize vector database schema."""
        if not self._conn:
            return
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY,
                title TEXT,
                summary TEXT,
                url TEXT,
                source TEXT,
                date TEXT,
                topic TEXT,
                embedding BLOB
            )
        """)
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS stories_vec USING vec0(
                embedding FLOAT[384]
            )
        """)
        self._conn.commit()

    def index_reports(self, reports: list[dict[str, Any]]) -> int:
        """Index reports into vector store."""
        self._ensure_vector_store()
        if not self._conn:
            return 0

        count = 0
        for report in reports:
            topic = report.get("topic", "")
            for column in report.get("columns") or []:
                for news in column.get("news_list") or []:
                    if not isinstance(news, dict):
                        continue
                    title = news.get("title", "")
                    summary = news.get("summary", "")
                    url = news.get("url", "")
                    source = news.get("source", "")
                    date = news.get("date", "")
                    
                    if not title or not summary:
                        continue
                    
                    # Generate embedding (placeholder - would use real embedding model)
                    text = f"{title}. {summary}"
                    embedding = self._simple_embedding(text)
                    
                    self._conn.execute(
                        "INSERT INTO stories (title, summary, url, source, date, topic, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (title, summary, url, source, date, topic, embedding)
                    )
                    count += 1
        self._conn.commit()
        return count

    def _simple_embedding(self, text: str) -> bytes:
        """Simple hash-based embedding (placeholder for real model)."""
        # Use hash as pseudo-embedding for demo
        import hashlib
        h = hashlib.md5(text.encode()).digest()
        # Pad to 384 dimensions (1536 bytes)
        arr = list(h) * (384 // 16)
        return bytes(arr[:384])

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search for relevant stories."""
        self._ensure_vector_store()
        if not self._conn:
            return []
        
        query_embedding = self._simple_embedding(query)
        
        cursor = self._conn.execute("""
            SELECT title, summary, url, source, date, topic,
                   vec_distance(embedding, ?) as distance
            FROM stories, stories_vec
            WHERE stories.id = stories_vec.rowid
            ORDER BY distance
            LIMIT ?
        """, (query_embedding, top_k))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "title": row[0],
                "summary": row[1],
                "url": row[2],
                "source": row[3],
                "date": row[4],
                "topic": row[5],
                "score": 1.0 - row[6] / 2.0,  # Convert distance to similarity
            })
        return results


async def answer_question(
    question: str,
    settings: AppSettings,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Answer a question using RAG over the report archive."""
    rag = RAGChat(settings, logger)
    
    # Load recent reports for indexing (if not already indexed)
    from .dashboard import load_catalog
    output_dir = Path(settings.output.directory)
    catalog = load_catalog(output_dir)
    rag.index_reports(catalog)
    
    # Search for relevant stories
    results = rag.search(question, top_k=5)
    
    if not results:
        return {
            "answer": "I couldn't find relevant information in the archive for your question.",
            "sources": [],
        }
    
    # Build context for LLM
    context_parts = []
    sources = []
    for r in results:
        context_parts.append(f"Title: {r['title']}\nSummary: {r['summary']}\nSource: {r['source']} ({r['date']})")
        sources.append({"title": r["title"], "url": r["url"], "source": r["source"]})
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Use Agently to generate answer (simplified - would use actual LLM call)
    from .collector import run_with_model_fallback
    from .config import AppSettings as AppSettingsClass
    
    prompt = f"""You are a helpful assistant answering questions about news from a daily briefing archive.

Context from the archive:
{context}

Question: {question}

Answer the question based only on the provided context. Cite sources by title. If the context doesn't contain the answer, say so."""

    # For now, return a structured response without LLM call
    return {
        "answer": f"Based on the archive, here's what I found:\n\n{context}",
        "sources": sources,
    }


__all__ = [
    "export_to_notion",
    "export_to_obsidian",
    "get_export_config",
    "ExportConfig",
    "answer_question",
    "RAGChat",
    "RAGConfig",
]