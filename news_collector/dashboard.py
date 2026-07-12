from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .dateutils import format_jalali, to_persian_numbers


_DASHBOARD_STYLE = """
:root{
  --bg:#0a0b0f; --bg-2:#0d0f15; --card:#12141c; --card-2:#171a24;
  --border:#232735; --border-hi:#323848;
  --text:#e9ebf2; --dim:#8b91a3; --faint:#565d70;
  --accent:#ff6a3d; --accent-2:#ffb35c; --lime:#d4ff4f;
  --glow:0 0 28px rgba(255,106,61,.28);
  --glow-soft:0 8px 34px -10px rgba(255,106,61,.35);
  --shadow:0 20px 50px -20px rgba(0,0,0,.7);
  --grad:linear-gradient(135deg,var(--accent),var(--accent-2));
  --spring:cubic-bezier(.22,1.2,.36,1);
  --mono:"JetBrains Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme: light){
  :root{
    --bg:#f2f3f7; --bg-2:#eceef4; --card:#ffffff; --card-2:#f7f8fb;
    --border:#dfe2ec; --border-hi:#c9cedd;
    --text:#171923; --dim:#5d6474; --faint:#9aa0b0;
    --accent:#e8501e; --accent-2:#f08c2e; --lime:#7fae00;
    --ok:#0e9e6e; --danger:#e0324b;
    --glow:0 0 24px rgba(232,80,30,.18);
    --glow-soft:0 8px 30px -12px rgba(232,80,30,.3);
    --shadow:0 18px 44px -22px rgba(23,25,35,.3);
  }
}
*{box-sizing:border-box; margin:0}
::selection{background:var(--accent); color:#fff}
html{scrollbar-color:var(--border-hi) transparent}
body{
  margin:0 auto; padding:0 clamp(16px,4vw,44px) 80px; max-width:72rem;
  font-family:"Vazirmatn",-apple-system,"Segoe UI",Tahoma,sans-serif;
  line-height:1.7; color:var(--text); background:var(--bg);
  background-image:
    radial-gradient(1000px 520px at 82% -140px, rgba(255,106,61,.13), transparent 62%),
    radial-gradient(800px 460px at 8% -80px, rgba(212,255,79,.05), transparent 60%),
    radial-gradient(circle, rgba(255,255,255,.045) 1px, transparent 1.4px);
  background-size:auto, auto, 26px 26px;
}
@media (prefers-color-scheme: light){
  body{background-image:
    radial-gradient(1000px 520px at 82% -140px, rgba(232,80,30,.09), transparent 62%),
    radial-gradient(circle, rgba(23,25,35,.05) 1px, transparent 1.4px);
    background-size:auto, 26px 26px;}
}
@keyframes rise{from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:none}}
@keyframes card-in{from{opacity:0; transform:translateY(12px) scale(.98)} to{opacity:1; transform:none}}
@media (prefers-reduced-motion: reduce){*{animation:none !important; transition:none !important}}
header{padding-top:44px; animation:rise .5s var(--spring) both; margin-bottom:28px}
.kicker{
  font-family:var(--mono); font-size:10px; letter-spacing:.32em; text-transform:uppercase;
  color:var(--accent-2); font-weight:600;
}
h1{font-size:clamp(1.8rem,4.6vw,2.6rem); font-weight:900; line-height:1.2; margin:8px 0 4px; letter-spacing:-.02em}
h1 i{font-style:normal; background:var(--grad); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent}
.subtitle{font-family:var(--mono); color:var(--faint); font-size:11px}
.rule{margin-top:18px; height:2px; background:var(--grad); box-shadow:var(--glow)}
.rule::after{content:none}
a{color:var(--accent-2); text-decoration:none}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(270px,1fr)); gap:14px}
.card{
  border:1px solid var(--border); background:var(--card); border-radius:16px;
  padding:17px 18px 12px; display:flex; flex-direction:column; gap:7px;
  position:relative; overflow:hidden;
  transition:transform .22s var(--spring), box-shadow .25s, border-color .25s;
  animation:card-in .45s var(--spring) both; animation-delay:calc(min(var(--i,0),14)*40ms);
}
.card::before{
  content:""; position:absolute; top:0; inset-inline:0; height:2px;
  background:var(--grad); opacity:0; transition:opacity .25s;
}
.card:hover{transform:translateY(-4px); box-shadow:var(--shadow); border-color:var(--border-hi)}
.card:hover::before{opacity:1}
.topic{
  font-family:var(--mono); font-size:9px; font-weight:600; letter-spacing:.22em;
  text-transform:uppercase; color:var(--accent-2);
}
.card h2{font-size:14.5px; font-weight:800; line-height:1.55; unicode-bidi:plaintext; text-align:start}
.card h2 a{color:inherit}
.card h2 a:hover{color:var(--accent-2)}
.meta{
  font-family:var(--mono); color:var(--faint); font-size:10px;
  margin-top:auto; padding-top:8px; direction:ltr; text-align:left;
}
.links{display:flex; gap:6px; border-top:1px solid var(--border); margin-top:8px; padding-top:10px; font-size:10px}
.links a{
  font-family:var(--mono); font-weight:600; color:var(--dim);
  border:1px solid var(--border); border-radius:7px; padding:4px 10px;
  margin-inline-end:0; transition:all .15s;
}
.links a:hover{color:var(--accent-2); border-color:var(--accent); box-shadow:var(--glow)}
"""


def _catalog_path(output_dir: Path) -> Path:
    return output_dir / "reports.json"


def load_catalog(output_dir: Path) -> list[dict[str, Any]]:
    path = _catalog_path(output_dir)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [entry for entry in raw if isinstance(entry, dict)] if isinstance(raw, list) else []


def append_to_catalog(output_dir: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = load_catalog(output_dir)
    marker = (entry.get("report_title"), entry.get("date"))
    catalog = [
        existing
        for existing in catalog
        if (existing.get("report_title"), existing.get("date")) != marker
    ]
    catalog.append(entry)
    catalog.sort(key=lambda item: str(item.get("generated_at") or ""), reverse=True)
    _catalog_path(output_dir).write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return catalog


def _format_date_fa(date_str: str) -> str:
    """Convert ISO date string (YYYY-MM-DD) to Persian date with Persian numbers."""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        return format_jalali(dt, include_weekday=True)
    except (ValueError, TypeError):
        return date_str


def _format_date_fa_short(date_str: str) -> str:
    """Convert ISO date string to short Persian date (DD/MM/YYYY with Persian numbers)."""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        return format_jalali(dt, include_weekday=False, short=True)
    except (ValueError, TypeError):
        return date_str


def render_dashboard(catalog: list[dict[str, Any]]) -> str:
    esc = html.escape
    parts = [
        "<!doctype html>",
        '<html lang="fa" dir="rtl">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>بایگانی گزارش‌ها — سردبیر</title>",
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">',
        '<link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/Vazirmatn-Variable.woff2">',
        f"<style>{_DASHBOARD_STYLE}</style>",
        '<style>'
        '@font-face {'
        '  font-family: "Vazirmatn";'
        '  src: url("/fonts/Vazirmatn-Variable.woff2") format("woff2");'
        '  font-weight: 100 900;'
        '  font-display: swap;'
        '  font-style: normal;'
        '}'
        '@font-face {'
        '  font-family: "Vazirmatn";'
        '  src: url("/fonts/Vazirmatn-Variable.woff2") format("woff2");'
        '  font-weight: 100 900;'
        '  font-display: swap;'
        '  font-style: italic;'
        '}'
        'body { font-family: "Vazirmatn", -apple-system, "Segoe UI", Tahoma, sans-serif; }'
        '</style>',
        "</head>",
        "<body>",
        "<header>",
        '<div class="kicker">Daily News Collector</div>',
        "<h1>بایگانی گزارش‌ها<i>.</i></h1>",
        f'<p class="subtitle">{to_persian_numbers(str(len(catalog)))} گزارش</p>',
        '<div class="rule"></div>',
        "</header>",
        '<div class="grid">',
    ]
    format_labels = {"markdown": "MD", "json": "JSON", "html": "مشاهده"}
    for index, entry in enumerate(catalog):
        title = esc(str(entry.get("report_title") or "بدون عنوان"))
        topic = esc(str(entry.get("topic") or ""))
        meta_bits = [
            esc(_format_date_fa(str(entry[key])))
            for key in ("date", "language")
            if entry.get(key)
        ]
        files = entry.get("files") if isinstance(entry.get("files"), dict) else {}
        links = [
            f'<a href="./{esc(str(file_name), quote=True)}">{format_labels.get(fmt, esc(fmt))}</a>'
            for fmt, file_name in files.items()
            if file_name
        ]
        parts.append(f'<article class="card" style="--i:{index}">')
        if topic:
            parts.append(f'<div class="topic">{topic}</div>')
        primary = files.get("html") or files.get("markdown")
        if primary:
            parts.append(f'<h2><a href="./{esc(str(primary), quote=True)}">{title}</a></h2>')
        else:
            parts.append(f"<h2>{title}</h2>")
        if meta_bits:
            parts.append(f'<p class="meta">{" &middot; ".join(meta_bits)}</p>')
        if links:
            parts.append(f'<p class="links">{"".join(links)}</p>')
        parts.append("</article>")
    parts.extend(["</div>", "</body>", "</html>"])
    return "\n".join(parts) + "\n"


def update_dashboard(
    output_dir: str | Path,
    entry: dict[str, Any],
    *,
    site_url: str = "",
) -> Path:
    resolved_dir = Path(output_dir)
    resolved_dir.mkdir(parents=True, exist_ok=True)
    catalog = append_to_catalog(resolved_dir, entry)
    dashboard_path = resolved_dir / "index.html"
    dashboard_path.write_text(render_dashboard(catalog), encoding="utf-8")

    from .feed import write_feed

    write_feed(resolved_dir, catalog, site_url=site_url)
    return dashboard_path


__all__ = ["append_to_catalog", "load_catalog", "render_dashboard", "update_dashboard"]