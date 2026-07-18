from __future__ import annotations

from typing import Any

from .textutils import ensure_markdown_rtl, wrap_mixed


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
            "action": "建议行动",
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
            "action": "اقدام پیشنهادی",
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
        "action": "Suggested action",
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
    title = wrap_mixed(report_title, language)
    topic_str = wrap_mixed(topic, language)
    lines = [
        f"# {title}",
        "",
        f"> {labels['generated_at']}: {generated_at}",
        f"> {labels['topic']}: {topic_str}",
        "",
    ]

    if tldr:
        lines.append(f"## {labels['tldr']}")
        lines.append("")
        for takeaway in tldr:
            lines.append(f"- {wrap_mixed(takeaway, language)}")
        lines.append("")

    for column in columns:
        col_title = wrap_mixed(column["title"], language)
        col_prologue = ensure_markdown_rtl(wrap_mixed(str(column.get("prologue", "")), language), language)
        lines.extend(
            [
                f"## {col_title}",
                "",
                f"### {labels['prologue']}",
                "",
                col_prologue,
                "",
                f"### {labels['news_list']}",
                "",
            ]
        )

        for news in column["news_list"]:
            news_title = wrap_mixed(news.get("title", ""), language)
            news_url = news.get("url", "")
            lines.append(f"- [{news_title}]({news_url})")
            meta_parts = []
            if news.get("source"):
                meta_parts.append(f"{labels['source']}: {news['source']}")
            if news.get("date"):
                meta_parts.append(f"{labels['date']}: {news['date']}")
            if meta_parts:
                lines.append(f"  - {' | '.join(meta_parts)}")
            summary_text = ensure_markdown_rtl(wrap_mixed(str(news.get("summary", "")), language), language)
            comment_text = ensure_markdown_rtl(wrap_mixed(str(news.get("recommend_comment", "")), language), language)
            lines.append(f"  - {labels['summary']}: {summary_text}")
            lines.append(f"  - {labels['comment']}: {comment_text}")
            action = str(news.get("action") or "").strip()
            action_reason = ensure_markdown_rtl(wrap_mixed(str(news.get("action_reason") or ""), language), language)
            if action:
                lines.append(f"  - {labels['action']}: {action}{': ' + action_reason if action_reason else ''}")
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
