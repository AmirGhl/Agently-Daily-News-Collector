from __future__ import annotations

from typing import Any


def _labels_for_language(language: str) -> dict[str, str]:
    normalized = language.lower()
    if "chinese" in normalized or normalized.startswith("zh"):
        return {
            "generated_at": "生成时间",
            "topic": "主题",
            "prologue": "导语",
            "news_list": "新闻列表",
            "source": "来源",
            "date": "日期",
            "summary": "摘要",
            "comment": "推荐理由",
            "model": "模型",
            "tldr": "要点速览",
            "read_source": "阅读原文",
        }
    if "persian" in normalized or "farsi" in normalized or normalized.startswith("fa"):
        return {
            "generated_at": "زمان تولید",
            "topic": "موضوع",
            "prologue": "مقدمه",
            "news_list": "فهرست اخبار",
            "source": "منبع",
            "date": "تاریخ",
            "summary": "خلاصه",
            "comment": "چرا مهم است",
            "model": "مدل",
            "tldr": "نکات کلیدی",
            "read_source": "مشاهده منبع",
        }
    return {
        "generated_at": "Generated At",
        "topic": "Topic",
        "prologue": "Prologue",
        "news_list": "News List",
        "source": "Source",
        "date": "Date",
        "summary": "Summary",
        "comment": "Why It Matters",
        "model": "Model",
        "tldr": "Key Takeaways",
        "read_source": "Read the source",
    }


def render_markdown(
    *,
    report_title: str,
    generated_at: str,
    topic: str,
    language: str,
    columns: list[dict[str, Any]],
    model_label: str,
    tldr: list[str] | None = None,
) -> str:
    labels = _labels_for_language(language)
    lines = [
        f"# {report_title}",
        "",
        f"> {labels['generated_at']}: {generated_at}",
        f"> {labels['topic']}: {topic}",
        "",
    ]

    if tldr:
        lines.extend([f"## {labels['tldr']}", ""])
        lines.extend(f"- {takeaway}" for takeaway in tldr)
        lines.append("")

    for column in columns:
        lines.extend(
            [
                f"## {column['title']}",
                "",
                f"### {labels['prologue']}",
                "",
                column["prologue"],
                "",
                f"### {labels['news_list']}",
                "",
            ]
        )

        for news in column["news_list"]:
            lines.append(f"- [{news.get('title', '')}]({news.get('url', '')})")
            meta_parts = []
            if news.get("source"):
                meta_parts.append(f"{labels['source']}: {news['source']}")
            if news.get("date"):
                meta_parts.append(f"{labels['date']}: {news['date']}")
            if meta_parts:
                lines.append(f"  - {' | '.join(meta_parts)}")
            lines.append(f"  - {labels['summary']}: {news.get('summary', '')}")
            lines.append(f"  - {labels['comment']}: {news.get('recommend_comment', '')}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "Powered by [Agently 4](https://github.com/AgentEra/Agently)",
            "",
            f"{labels['model']}: {model_label}",
        ]
    )

    return "\n".join(lines).strip() + "\n"
