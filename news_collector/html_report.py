from __future__ import annotations

import html
import re
from typing import Any

from .markdown import _labels_for_language
from .textutils import strip_greeting

_RTL_MARKERS = ("persian", "farsi", "arabic", "hebrew", "urdu")
_RTL_PREFIXES = ("fa", "ar", "he", "ur")

_KIND_LABELS = {
    "repo": ("REPO", "k-repo"),
    "release": ("RELEASE", "k-rel"),
    "advisory": ("SECURITY", "k-sec"),
}

_UI_LABELS = {
    "fa": {
        "toc": "فهرست بخش‌ها",
        "min_read": "دقیقه مطالعه",
        "stories": "مطلب",
        "sections": "بخش",
        "end": "پایان گزارش",
        "new": "تازه",
        "copy": "کپی",
        "copied": "کپی شد ✓",
        "theme": "جوهر / کاغذ",
        "print": "چاپ / PDF",
        "why_pick": "چرا انتخاب شد",
        "top": "بازگشت به بالا",
    },
    "en": {
        "toc": "Sections",
        "min_read": "min read",
        "stories": "stories",
        "sections": "sections",
        "end": "End of briefing",
        "new": "new",
        "copy": "Copy",
        "copied": "Copied ✓",
        "theme": "Ink / Paper",
        "print": "Print / PDF",
        "why_pick": "Why it was picked",
        "top": "Back to top",
    },
}

# «جوهر و کاغذ» — ink & paper editorial design, matching the panel's reader.
# Hairlines instead of boxes, serif headlines, paper-grain atmosphere,
# two themes (ink dark / paper light), fully self-contained.
_PAGE_STYLE = """
:root{
  --bg:#141312; --surface:#1a1917; --well:#211f1c;
  --line:#2b2926; --linehi:#3e3a34;
  --ink:#ece7dc; --dim:#a49e90; --faint:#706b5e;
  --accent:#e2603f; --accent-dim:#b34a39;
  --ok:#5cae89; --warn:#c9a04a; --bad:#d95c6a;
  --mono:'JetBrains Mono',ui-monospace,Consolas,monospace;
  --sans:'Vazirmatn','Segoe UI',Tahoma,sans-serif;
  --serif:'Noto Naskh Arabic','Vazirmatn',Georgia,serif;
  --grain:.028;
}
html[data-theme="paper"]{
  --bg:#f5f1e6; --surface:#fbf8f0; --well:#ece7d8;
  --line:#ddd7c6; --linehi:#c4bda8;
  --ink:#201d17; --dim:#5d574a; --faint:#948d78;
  --accent:#b32d15; --accent-dim:#d4553f;
  --ok:#1e7d52; --warn:#8a6d1f; --bad:#b03246;
  --grain:.05;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scrollbar-color:var(--linehi) transparent;scroll-behavior:smooth}
body{
  font-family:var(--sans); background:var(--bg); color:var(--ink);
  font-size:14.5px; line-height:1.9; min-height:100dvh;
  -webkit-font-smoothing:antialiased;
  transition:background .25s ease,color .25s ease;
}
body::after{
  content:"";position:fixed;inset:0;z-index:99;pointer-events:none;
  opacity:var(--grain);
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E");
}
::selection{background:color-mix(in srgb,var(--accent) 25%,transparent)}
a{color:inherit}
button{font:inherit;color:inherit;background:none;border:none;cursor:pointer}
:focus-visible{outline:1.5px solid var(--accent);outline-offset:3px;border-radius:2px}
[dir="auto"]{unicode-bidi:plaintext}
.wrap{max-width:680px;margin-inline:auto;padding:0 22px}

/* ———— reading progress ———— */
#readbar{position:fixed;top:0;inset-inline:0;height:2px;z-index:50}
#readbar i{display:block;height:100%;width:0%;background:var(--accent)}

/* ———— floating tools ———— */
.tools{
  position:fixed;top:14px;inset-inline-end:14px;z-index:40;display:flex;gap:6px;
}
.tools button{
  width:34px;height:34px;display:grid;place-items:center;border-radius:9px;
  color:var(--faint);background:color-mix(in srgb,var(--surface) 82%,transparent);
  border:1px solid var(--line);backdrop-filter:blur(6px);
  transition:color .15s,border-color .15s,transform .15s;
}
.tools button:hover{color:var(--ink);border-color:var(--linehi);transform:translateY(-1px)}
.tools svg{width:15px;height:15px}

/* ———— masthead ———— */
.paper{padding:56px 0 90px}
.kicker{
  font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;color:var(--faint);
  direction:ltr;display:flex;gap:14px;flex-wrap:wrap;
}
html[dir="rtl"] .kicker{justify-content:flex-start;text-align:right}
.kicker b{color:var(--accent);font-weight:600}
h1{
  font-family:var(--serif);font-size:clamp(25px,4.6vw,34px);font-weight:700;
  line-height:1.65;margin-top:12px;unicode-bidi:plaintext;
}
.byline{font-size:12px;color:var(--dim);margin-top:8px}
.byline b{color:var(--accent);font-weight:600}
.rule{border:none;border-top:1px solid var(--line);margin:22px 0}
.rule.dbl{border-top:3px double var(--linehi);margin:20px 0 26px}

/* ———— animations ———— */
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.masthead{animation:rise .5s ease backwards}
.tldr{animation:rise .5s .08s ease backwards}
.toc{animation:rise .5s .14s ease backwards}
.reveal{opacity:0;transform:translateY(14px);transition:opacity .55s ease,transform .55s cubic-bezier(.22,1,.36,1)}
.reveal.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition-duration:.01ms!important}
  .reveal{opacity:1;transform:none}
  html{scroll-behavior:auto}
}

/* ———— tldr ———— */
.tldr{border-block:1px solid var(--line);padding:18px 0 20px;margin-bottom:8px}
.tldr h2{font-family:var(--serif);font-size:14.5px;font-weight:700;color:var(--dim);margin-bottom:12px}
.tldr ol{list-style:none;display:flex;flex-direction:column;gap:11px}
.tldr li{display:flex;gap:12px;font-size:13.5px;color:var(--dim);line-height:2}
.tldr li i{font-style:normal;font-family:var(--mono);font-size:11px;color:var(--accent);margin-top:3px;flex-shrink:0}

/* ———— toc ———— */
.toc{
  position:sticky;top:0;z-index:30;display:flex;flex-wrap:wrap;gap:7px 20px;
  padding:13px 0 13px;border-bottom:1px solid var(--line);font-size:12px;
  background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(8px);
}
.toc a{display:flex;gap:7px;align-items:baseline;color:var(--dim);text-decoration:none;transition:color .15s}
.toc a:hover,.toc a.on{color:var(--accent)}
.toc i{font-style:normal;font-family:var(--mono);font-size:9px;color:var(--accent)}

/* ———— columns ———— */
.colhead{display:flex;align-items:baseline;gap:11px;margin:42px 0 6px;scroll-margin-top:76px}
.colhead .n{font-family:var(--mono);font-size:10px;color:var(--accent)}
.colhead h2{font-family:var(--serif);font-size:19px;font-weight:700;unicode-bidi:plaintext;line-height:1.6}
.colhead .cnt{font-family:var(--mono);font-size:9px;color:var(--faint)}
.colhead::after{content:"";flex:1;height:1px;background:var(--line);align-self:center}
.prologue{font-size:13.5px;color:var(--dim);line-height:2.05;unicode-bidi:plaintext;margin-top:8px}

/* ———— story ———— */
.story{padding:24px 0;border-bottom:1px solid var(--line)}
.story:last-of-type{border-bottom:none}
.story .meta{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-family:var(--mono);font-size:9px;direction:ltr}
html[dir="rtl"] .story .meta{justify-content:flex-end}
.story .meta .k{letter-spacing:.08em;font-weight:600}
.k.k-repo{color:var(--accent)} .k.k-rel,.k.k-ph{color:var(--ok)} .k.k-sec{color:var(--bad)}
.k.k-new{color:var(--ok);font-weight:800}
.k.k-hn,.k.k-com{color:var(--warn)} .k.k-web{color:var(--faint)}
.story .meta .src{color:var(--faint)}
.story h3{font-family:var(--serif);font-size:17.5px;font-weight:600;line-height:1.8;margin-top:7px;unicode-bidi:plaintext}
.story h3 a{text-decoration:none;transition:color .15s}
.story h3 a:hover{color:var(--accent)}
.figure{margin:14px 0 4px;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--well)}
.figure img{display:block;width:100%;max-height:340px;object-fit:cover;filter:saturate(.92)}
html[data-theme="ink"] .figure img{filter:saturate(.88) brightness(.94)}
.story .body{font-size:13.5px;color:var(--dim);line-height:2.05;margin-top:10px;unicode-bidi:plaintext}
.story .body p{margin-bottom:.55rem}
.why{margin-top:13px;padding-inline-start:12px;border-inline-start:2px solid color-mix(in srgb,var(--accent) 38%,var(--line))}
.why b{display:block;font-size:10px;font-weight:600;color:var(--faint)}
.why p{font-size:12.5px;color:var(--dim);line-height:2;margin-top:2px;unicode-bidi:plaintext}
.story .foot{display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap}
.story .lnk{
  display:inline-block;font-family:var(--mono);font-size:10px;color:var(--accent);
  text-decoration:none;direction:ltr;max-width:70%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.story .lnk:hover{text-decoration:underline}
.story .cpy{
  font-size:10px;color:var(--faint);padding:2px 9px;border:1px solid var(--line);border-radius:6px;
  transition:color .15s,border-color .15s;
}
.story .cpy:hover{color:var(--accent);border-color:var(--linehi)}

/* ———— end / footer ———— */
.endmark{margin-top:46px;text-align:center;font-family:var(--serif);font-size:11.5px;color:var(--faint)}
.endmark::before{content:"❖";display:block;font-size:10px;color:var(--accent);margin-bottom:8px;opacity:.7}
footer{
  margin-top:26px;padding-top:16px;border-top:1px solid var(--line);text-align:center;
  font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;color:var(--faint);direction:ltr;
}
footer a{color:var(--accent);text-decoration:none}

@media(max-width:520px){
  .paper{padding-top:48px}
  .figure img{max-height:230px}
  .story .lnk{max-width:100%}
}

/* ———— print ———— */
@media print{
  :root,html[data-theme="paper"],html[data-theme="ink"]{
    --bg:#fff;--surface:#fff;--well:#fff;--line:#bbb;--linehi:#777;
    --ink:#000;--dim:#222;--faint:#555;--accent:#8a1d0d;--grain:0;
  }
  #readbar,.tools,.toc,.story .cpy,body::after{display:none!important}
  body{background:#fff;font-size:12.5px}
  .paper{padding:0 0 20px}
  .story,.tldr{break-inside:avoid}
  .figure img{max-height:220px}
  .story .lnk{white-space:normal;word-break:break-all}
  .masthead,.tldr,.toc,.reveal{animation:none;opacity:1;transform:none}
}
"""

_PAGE_SCRIPT = """
(function(){
  "use strict";
  /* theme */
  var root = document.documentElement;
  var saved = null;
  try { saved = localStorage.getItem("ink-theme"); } catch(e){}
  if (saved === "ink" || saved === "paper") root.dataset.theme = saved;
  var themeBtn = document.getElementById("themeBtn");
  if (themeBtn) themeBtn.addEventListener("click", function(){
    var next = root.dataset.theme === "ink" ? "paper" : "ink";
    root.dataset.theme = next;
    try { localStorage.setItem("ink-theme", next); } catch(e){}
  });
  var printBtn = document.getElementById("printBtn");
  if (printBtn) printBtn.addEventListener("click", function(){ window.print(); });
  var topBtn = document.getElementById("topBtn");
  if (topBtn) topBtn.addEventListener("click", function(){ window.scrollTo({top:0, behavior:"smooth"}); });

  /* reading progress */
  var fill = document.getElementById("readfill");
  window.addEventListener("scroll", function(){
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    if (fill) fill.style.width = (max > 0 ? Math.min(100, (h.scrollTop / max) * 100) : 0) + "%";
  }, {passive:true});

  /* copy buttons */
  document.querySelectorAll(".cpy").forEach(function(b){
    b.addEventListener("click", function(){
      var text = (b.dataset.t ? b.dataset.t + "\\n" : "") + (b.dataset.u || "");
      var done = function(){
        var old = b.textContent;
        b.textContent = b.dataset.ok || "✓";
        setTimeout(function(){ b.textContent = old; }, 1600);
      };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function(){});
    });
  });

  /* hide broken images */
  document.querySelectorAll(".figure img").forEach(function(img){
    img.addEventListener("error", function(){
      var f = img.closest(".figure");
      if (f) f.remove();
    });
  });

  if (!("IntersectionObserver" in window)) {
    document.querySelectorAll(".reveal").forEach(function(el){ el.classList.add("in"); });
    return;
  }
  /* scroll reveal */
  var ro = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if (entry.isIntersecting){ entry.target.classList.add("in"); ro.unobserve(entry.target); }
    });
  }, {rootMargin:"0px 0px -8% 0px"});
  document.querySelectorAll(".reveal").forEach(function(el){ ro.observe(el); });

  /* active toc */
  var links = document.querySelectorAll(".toc a");
  if (links.length){
    var map = {};
    links.forEach(function(a){ map[a.getAttribute("href").slice(1)] = a; });
    var so = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if (entry.isIntersecting){
          links.forEach(function(a){ a.classList.remove("on"); });
          var link = map[entry.target.id];
          if (link) link.classList.add("on");
        }
      });
    }, {rootMargin:"-12% 0px -74% 0px"});
    document.querySelectorAll(".colhead[id]").forEach(function(s){ so.observe(s); });
  }
})();
"""

_SVG_THEME = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
    '<path d="M12 3v18M12 3a9 9 0 0 1 0 18" fill="currentColor" stroke="none" opacity=".35"/></svg>'
)
_SVG_PRINT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M6 9V3h12v6"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
    '<rect x="6" y="14" width="12" height="7"/></svg>'
)
_SVG_TOP = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 19V5M5 12l7-7 7 7"/></svg>'
)


def _is_rtl_language(language: str) -> bool:
    normalized = language.strip().lower()
    return any(marker in normalized for marker in _RTL_MARKERS) or normalized.startswith(_RTL_PREFIXES)


def _ui_labels(language: str) -> dict[str, str]:
    return _UI_LABELS["fa" if _is_rtl_language(language) else "en"]


def _anchor(title: str, index: int) -> str:
    slug = re.sub(r"[^\w]+", "-", title.lower()).strip("-")
    return f"col-{index}-{slug or 'section'}"


def _paragraphs(text: str) -> str:
    esc = html.escape
    parts = [part.strip() for part in text.split("\n") if part.strip()]
    if not parts:
        return ""
    return "".join(f'<p dir="auto">{esc(part)}</p>' for part in parts)


def _badge_for(news: dict[str, Any]) -> tuple[str, str] | None:
    kind = str(news.get("kind") or "")
    if kind in _KIND_LABELS:
        return _KIND_LABELS[kind]
    source = str(news.get("source") or "").lower()
    url = str(news.get("url") or "").lower()
    if "advisor" in source or "security" in source:
        return ("SECURITY", "k-sec")
    if "release" in source:
        return ("RELEASE", "k-rel")
    if "github" in source or re.search(r"github\.com/[^/]+/[^/]+/?$", url):
        return ("REPO", "k-repo")
    if "hacker" in source:
        return ("HN", "k-hn")
    if "product hunt" in source:
        return ("LAUNCH", "k-ph")
    if any(marker in source for marker in ("reddit", "lobster", "dev.to", "daily.dev")):
        return ("COMMUNITY", "k-com")
    if source:
        return ("WEB", "k-web")
    return None


def _reading_minutes(columns: list[dict[str, Any]], tldr: list[str] | None) -> int:
    words = 0
    for takeaway in tldr or []:
        words += len(str(takeaway).split())
    for column in columns:
        words += len(str(column.get("prologue") or "").split())
        for news in column.get("news_list") or []:
            if isinstance(news, dict):
                words += len(str(news.get("title") or "").split())
                words += len(str(news.get("summary") or "").split())
                words += len(str(news.get("recommend_comment") or "").split())
    return max(1, round(words / 180))


def render_html(
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
    ui = _ui_labels(language)
    direction = "rtl" if _is_rtl_language(language) else "ltr"
    esc = html.escape

    tldr_clean = [strip_greeting(str(item).strip()) for item in (tldr or []) if str(item or "").strip()]
    story_count = sum(len(column.get("news_list") or []) for column in columns)
    minutes = _reading_minutes(columns, tldr_clean)
    all_news = [
        news
        for column in columns
        for news in (column.get("news_list") or [])
        if isinstance(news, dict)
    ]
    new_count = sum(1 for news in all_news if news.get("is_new"))
    # The NEW badge only matters when repeats are in the mix (--allow-repeats);
    # when history filtering is on, every story is new and badges are noise.
    has_repeats = any(news.get("is_new") is False for news in all_news)

    parts = [
        "<!doctype html>",
        f'<html lang="{esc(language[:2].lower() or "en")}" dir="{direction}" data-theme="ink">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(report_title)}</title>",
        f'<meta name="description" content="{esc(" · ".join(tldr_clean[:2])[:280])}">',
        # Progressive enhancement: falls back to Georgia/Tahoma offline.
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;800&family=Noto+Naskh+Arabic:wght@500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">',
        f"<style>{_PAGE_STYLE}</style>",
        "</head>",
        "<body>",
        '<div id="readbar" aria-hidden="true"><i id="readfill"></i></div>',
        '<div class="tools">',
        f'<button id="topBtn" title="{esc(ui["top"])}" aria-label="{esc(ui["top"])}">{_SVG_TOP}</button>',
        f'<button id="printBtn" title="{esc(ui["print"])}" aria-label="{esc(ui["print"])}">{_SVG_PRINT}</button>',
        f'<button id="themeBtn" title="{esc(ui["theme"])}" aria-label="{esc(ui["theme"])}">{_SVG_THEME}</button>',
        "</div>",
        '<div class="wrap"><article class="paper">',
        '<header class="masthead">',
        '<div class="kicker">',
        f"<span>{esc(generated_at[:10])}</span>",
        f"<span>{len(columns)} {esc(ui['sections']).upper() if direction == 'ltr' else esc(ui['sections'])} · {story_count} {esc(ui['stories'])}"
        + (f" · ✦ {new_count} {esc(ui['new'])}" if has_repeats and new_count else "")
        + "</span>",
        f"<span>~{minutes} {esc(ui['min_read'])}</span>",
        f'<b dir="auto">{esc(topic)}</b>',
        "</div>",
        f'<h1 dir="auto">{esc(report_title)}</h1>',
        f'<div class="byline">{esc(labels["model"])}: <span dir="ltr">{esc(model_label)}</span></div>',
        '<hr class="rule dbl">',
        "</header>",
    ]

    if tldr_clean:
        parts.append('<aside class="tldr">')
        parts.append(f"<h2>{esc(labels['tldr'])}</h2>")
        parts.append("<ol>")
        parts.extend(
            f'<li><i>{index:02d}</i><span dir="auto">{esc(takeaway)}</span></li>'
            for index, takeaway in enumerate(tldr_clean, 1)
        )
        parts.append("</ol>")
        parts.append("</aside>")

    if len(columns) > 1:
        parts.append(f'<nav class="toc" aria-label="{esc(ui["toc"])}">')
        for index, column in enumerate(columns):
            title = str(column.get("title") or "")
            parts.append(
                f'<a href="#{_anchor(title, index)}"><i>{index + 1:02d}</i>'
                f'<span dir="auto">{esc(title)}</span></a>'
            )
        parts.append("</nav>")

    for index, column in enumerate(columns):
        column_title = str(column.get("title") or "")
        news_list = [news for news in (column.get("news_list") or []) if isinstance(news, dict)]
        parts.append(
            f'<div class="colhead reveal" id="{_anchor(column_title, index)}">'
            f'<span class="n">{index + 1:02d}</span>'
            f'<h2 dir="auto">{esc(column_title)}</h2>'
            f'<span class="cnt">{len(news_list)}</span></div>'
        )
        prologue = strip_greeting(str(column.get("prologue") or "").strip())
        if prologue:
            parts.append(f'<p class="prologue reveal" dir="auto">{esc(prologue)}</p>')

        for news in news_list:
            parts.append('<div class="story reveal">')

            meta_bits = ['<div class="meta">']
            if has_repeats and news.get("is_new"):
                meta_bits.append(f'<span class="k k-new">✦ {esc(ui["new"]).upper()}</span>')
            badge = _badge_for(news)
            if badge:
                meta_bits.append(f'<span class="k {badge[1]}">{badge[0]}</span>')
            source = str(news.get("source") or "").strip()
            if source:
                meta_bits.append(f'<span class="src">{esc(source)}</span>')
            date = str(news.get("date") or "").strip()
            if date:
                meta_bits.append(f'<span class="src">{esc(date[:10])}</span>')
            relevance = news.get("relevance_score")
            if isinstance(relevance, (int, float)):
                meta_bits.append(f'<span class="src">★ {int(relevance)}/10</span>')
            meta_bits.append("</div>")
            parts.append("".join(meta_bits))

            title = esc(str(news.get("title") or ""))
            url = esc(str(news.get("url") or ""), quote=True)
            if url:
                parts.append(f'<h3 dir="auto"><a href="{url}" target="_blank" rel="noreferrer">{title}</a></h3>')
            else:
                parts.append(f'<h3 dir="auto">{title}</h3>')

            image = str(news.get("image") or "").strip()
            if image.startswith(("http://", "https://")):
                parts.append(
                    f'<figure class="figure"><img src="{esc(image, quote=True)}" '
                    f'alt="{title}" loading="lazy" decoding="async"></figure>'
                )

            summary = strip_greeting(str(news.get("summary") or news.get("brief") or "").strip())
            if summary:
                parts.append(f'<div class="body">{_paragraphs(summary)}</div>')

            comment = strip_greeting(str(news.get("recommend_comment") or "").strip())
            if comment:
                parts.append(
                    f'<aside class="why"><b>{esc(labels["comment"])}</b>'
                    f'<p dir="auto">{esc(comment)}</p></aside>'
                )

            if url:
                parts.append(
                    '<div class="foot">'
                    f'<a class="lnk" href="{url}" target="_blank" rel="noreferrer">{url} ↗</a>'
                    f'<button type="button" class="cpy" data-t="{title}" data-u="{url}" '
                    f'data-ok="{esc(ui["copied"])}">{esc(ui["copy"])}</button>'
                    "</div>"
                )
            parts.append("</div>")

    parts.extend(
        [
            f'<div class="endmark">— {esc(ui["end"])} —</div>',
            "<footer>",
            f'{esc(generated_at)} · <span>{esc(model_label)}</span> · '
            'Powered by <a href="https://github.com/AgentEra/Agently">AGENTLY 4</a>',
            "</footer>",
            "</article></div>",
            f"<script>{_PAGE_SCRIPT}</script>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts) + "\n"


__all__ = ["render_html"]
