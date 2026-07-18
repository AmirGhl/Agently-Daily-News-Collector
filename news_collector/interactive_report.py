#!/usr/bin/env python3
"""Generate an interactive HTML report template with htmx + Alpine.js."""

# The interactive report template - builds upon the existing "ink & paper" design
# but adds htmx/Alpine for search, filter, reader mode, and export features.

INTERACTIVE_REPORT_TEMPLATE = '''<!doctype html>
<html lang="{language_code}" dir="{direction}" data-theme="{theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped_report_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/Vazirmatn-Variable.woff2">

<style>
/* ─── Vazirmatn variable font (self-hosted) ─── */
@font-face {{
  font-family: "Vazirmatn";
  src: url("/fonts/Vazirmatn-Variable.woff2") format("woff2");
  font-weight: 100 900;
  font-display: swap;
  font-style: normal;
}}
@font-face {{
  font-family: "Vazirmatn";
  src: url("/fonts/Vazirmatn-Variable.woff2") format("woff2");
  font-weight: 100 900;
  font-display: swap;
  font-style: italic;
}}

/* ─── Theme tokens (ink & paper) ─── */
:root{{
  --bg:#141312; --surface:#1a1917; --well:#211f1c;
  --line:#2b2926; --linehi:#3e3a34;
  --ink:#ece7dc; --dim:#a49e90; --faint:#706b5e;
  --accent:#e2603f; --accent-dim:#b34a39;
  --ok:#5cae89; --warn:#c9a04a; --bad:#d95c6a;
  --mono:'JetBrains Mono',ui-monospace,Consolas,monospace;
  --sans:'Vazirmatn','Segoe UI',Tahoma,sans-serif;
  --serif:'Noto Naskh Arabic','Vazirmatn',Georgia,serif;
  --grain:.028;
}}
html[data-theme="paper"]{{
  --bg:#f5f1e6; --surface:#fbf8f0; --well:#ece7d8;
  --line:#ddd7c6; --linehi:#c4bda8;
  --ink:#201d17; --dim:#5d574a; --faint:#948d78;
  --accent:#b32d15; --accent-dim:#d4553f;
  --ok:#1e7d52; --warn:#8a6d1f; --bad:#b03246;
  --grain:.05;
}}

/* ─── Reset & base ─── */
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scrollbar-color:var(--linehi) transparent;scroll-behavior:smooth}}
body{{
  font-family:var(--sans); background:var(--bg); color:var(--ink);
  font-size:14.5px; line-height:1.9; min-height:100dvh;
  -webkit-font-smoothing:antialiased;
  transition:background .25s ease,color .25s ease;
}}
body::after{{
  content:"";position:fixed;inset:0;z-index:99;pointer-events:none;
  opacity:var(--grain);
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E");
}}
::selection{{background:color-mix(in srgb,var(--accent) 25%,transparent)}}
a{{color:inherit}}
button{{font:inherit;color:inherit;background:none;border:none;cursor:pointer}}
:focus-visible{{outline:1.5px solid var(--accent);outline-offset:3px;border-radius:2px}}
[dir="auto"]{{unicode-bidi:plaintext}}
.wrap{{max-width:720px;margin-inline:auto;padding:0 22px}}

/* ─── Reading progress bar ─── */
#readbar{{position:fixed;top:0;inset-inline:0;height:2px;z-index:50}}
#readbar i{{display:block;height:100%;width:0%;background:var(--accent)}}

/* ─── Floating tools ─── */
.tools{{
  position:fixed;top:14px;inset-inline-end:14px;z-index:40;display:flex;gap:6px;
}}
.tools button{{
  width:34px;height:34px;display:grid;place-items:center;border-radius:9px;
  color:var(--faint);background:color-mix(in srgb,var(--surface) 82%,transparent);
  border:1px solid var(--line);backdrop-filter:blur(6px);
  transition:color .15s,border-color .15s,transform .15s;
}}
.tools button:hover{{color:var(--ink);border-color:var(--linehi);transform:translateY(-1px)}}
.tools svg{{width:15px;height:15px}}

/* ─── Masthead ─── */
.paper{{padding:56px 0 90px}}
.kicker{{
  font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;color:var(--faint);
  direction:ltr;display:flex;gap:14px;flex-wrap:wrap;
}}
html[dir="rtl"] .kicker{{justify-content:flex-start;text-align:right}}
.kicker b{{color:var(--accent);font-weight:600}}
h1{{
  font-family:var(--serif);font-size:clamp(25px,4.6vw,34px);font-weight:700;
  line-height:1.65;margin-top:12px;unicode-bidi:plaintext;
}}
.byline{{font-size:12px;color:var(--dim);margin-top:8px}}
.byline b{{color:var(--accent);font-weight:600}}
.rule{{border:none;border-top:1px solid var(--line);margin:22px 0}}
.rule.dbl{{border-top:3px double var(--linehi);margin:20px 0 26px}}

/* ─── Animations ─── */
@keyframes rise{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:none}}}}
.masthead{{animation:rise .5s ease backwards}}
.tldr{{animation:rise .5s .08s ease backwards}}
.toc{{animation:rise .5s .14s ease backwards}}
.reveal{{opacity:0;transform:translateY(14px);transition:opacity .55s ease,transform .55s cubic-bezier(.22,1,.36,1)}}
.reveal.in{{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){{
  *,*::before,*::after{{animation:none!important;transition-duration:.01ms!important}}
  .reveal{{opacity:1;transform:none}}
  html{{scroll-behavior:auto}}
}}

/* ─── TL;DR ─── */
.tldr{{border-block:1px solid var(--line);padding:18px 0 20px;margin-bottom:8px}}
.tldr h2{{font-family:var(--serif);font-size:14.5px;font-weight:700;color:var(--dim);margin-bottom:12px}}
.tldr ol{{list-style:none;display:flex;flex-direction:column;gap:11px}}
.tldr li{{display:flex;gap:12px;font-size:13.5px;color:var(--dim);line-height:2}}
.tldr li i{{font-style:normal;font-family:var(--mono);font-size:11px;color:var(--accent);margin-top:3px;flex-shrink:0}}

/* ─── TOC ─── */
.toc{{
  position:sticky;top:0;z-index:30;display:flex;flex-wrap:wrap;gap:7px 20px;
  padding:13px 0 13px;border-bottom:1px solid var(--line);font-size:12px;
  background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(8px);
}}
.toc a{{display:flex;gap:7px;align-items:baseline;color:var(--dim);text-decoration:none;transition:color .15s}}
.toc a:hover,.toc a.on{{color:var(--accent)}}
.toc i{{font-style:normal;font-family:var(--mono);font-size:9px;color:var(--accent)}}

/* ─── Columns ─── */
.colhead{{display:flex;align-items:baseline;gap:11px;margin:42px 0 6px;scroll-margin-top:76px}}
.colhead .n{{font-family:var(--mono);font-size:10px;color:var(--accent)}}
.colhead h2{{font-family:var(--serif);font-size:19px;font-weight:700;unicode-bidi:plaintext;line-height:1.6}}
.colhead .cnt{{font-family:var(--mono);font-size:9px;color:var(--faint)}}
.colhead::after{{content:"";flex:1;height:1px;background:var(--line);align-self:center}}
.prologue{{font-size:13.5px;color:var(--dim);line-height:2.05;unicode-bidi:plaintext;margin-top:8px}}

/* ─── Story ─── */
.story{{padding:24px 0;border-bottom:1px solid var(--line)}}
.story:last-of-type{{border-bottom:none}}
.story .meta{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-family:var(--mono);font-size:9px;direction:ltr}}
html[dir="rtl"] .story .meta{{justify-content:flex-end}}
.story .meta .k{{letter-spacing:.08em;font-weight:600}}
.k.k-repo{{color:var(--accent)}} .k.k-rel,.k.k-ph{{color:var(--ok)}} .k.k-sec{{color:var(--bad)}}
.k.k-new{{color:var(--ok);font-weight:800}}
.k.k-hn,.k.k-com{{color:var(--warn)}} .k.k-web{{color:var(--faint)}}
.story .meta .src{{color:var(--faint)}}
.story h3{{font-family:var(--serif);font-size:17.5px;font-weight:600;line-height:1.8;margin-top:7px;unicode-bidi:plaintext}}
.story h3 a{{text-decoration:none;transition:color .15s}}
.story h3 a:hover{{color:var(--accent)}}
.figure{{margin:14px 0 4px;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--well)}}
.figure img{{display:block;width:100%;max-height:340px;object-fit:cover;filter:saturate(.92)}}
html[data-theme="ink"] .figure img{{filter:saturate(.88) brightness(.94)}}
.story .body{{font-size:13.5px;color:var(--dim);line-height:2.05;margin-top:10px;unicode-bidi:plaintext}}
.story .body p{{margin-bottom:.55rem}}
.why{{margin-top:13px;padding-inline-start:12px;border-inline-start:2px solid color-mix(in srgb,var(--accent) 38%,var(--line))}}
.why b{{display:block;font-size:10px;font-weight:600;color:var(--faint)}}
.why p{{font-size:12.5px;color:var(--dim);line-height:2;margin-top:2px;unicode-bidi:plaintext}}
.decision{{margin-top:13px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--well)}}
.decision-head{{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:9px;color:var(--faint)}}
.decision-pill{{padding:2px 7px;border:1px solid var(--linehi);border-radius:999px;font-weight:700;letter-spacing:.05em;color:var(--accent)}}
.decision-pill.u-high{{color:var(--bad);border-color:var(--bad)}} .decision-pill.u-medium{{color:var(--warn);border-color:var(--warn)}} .decision-pill.u-low{{color:var(--ok);border-color:var(--ok)}}
.decision p{{font-size:12.5px;color:var(--dim);line-height:1.9;margin-top:5px;unicode-bidi:plaintext}}
.morning{{margin:18px 0 8px;padding:16px;border:1px solid var(--line);border-radius:10px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 9%,var(--surface)),var(--surface))}}
.morning h2{{font-family:var(--serif);font-size:15px;margin-bottom:10px}}
.morning-list{{display:grid;gap:8px}}
.morning-item{{display:grid;grid-template-columns:auto 1fr;gap:8px;align-items:start;padding-top:8px;border-top:1px solid var(--line)}}
.morning-item:first-child{{border-top:none;padding-top:0}}
.morning-item a{{font-size:12.5px;line-height:1.7;text-decoration:none;unicode-bidi:plaintext}} .morning-item a:hover{{color:var(--accent)}}
.story .foot{{display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap}}
.story .lnk{{
  display:inline-block;font-family:var(--mono);font-size:10px;color:var(--accent);
  text-decoration:none;direction:ltr;max-width:70%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}}
.story .lnk:hover{{text-decoration:underline}}
.story .cpy{{
  font-size:10px;color:var(--faint);padding:2px 9px;border:1px solid var(--line);border-radius:6px;
  transition:color .15s,border-color .15s;
}}
.story .cpy:hover{{color:var(--accent);border-color:var(--linehi)}}

/* ─── End / Footer ─── */
.endmark{{margin-top:46px;text-align:center;font-family:var(--serif);font-size:11.5px;color:var(--faint)}}
.endmark::before{{content:"❖";display:block;font-size:10px;color:var(--accent);margin-bottom:8px;opacity:.7}}
footer{{
  margin-top:26px;padding-top:16px;border-top:1px solid var(--line);text-align:center;
  font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;color:var(--faint);direction:ltr;
}}
footer a{{color:var(--accent);text-decoration:none}}

/* ─── Reader mode overlay ─── */
.reader-overlay{{
  position:fixed;inset:0;z-index:100;background:var(--bg);display:none;
  flex-direction:column;overflow-y:auto;padding:24px 16px 80px;
}}
.reader-overlay.open{{display:flex}}
.reader-header{{
  display:flex;align-items:center;gap:10px;padding:12px 0 8px;border-bottom:1px solid var(--line);
  position:sticky;top:0;background:var(--bg);z-index:10;
}}
.reader-content{{max-width:720px;margin:0 auto;padding:24px 0;flex:1}}

/* ─── Search/Filter bar ─── */
.filter-bar{{
  position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;gap:8px;align-items:center;
  padding:12px 0;border-bottom:1px solid var(--line);
  background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(8px);
}}
.filter-search{{
  flex:1;min-width:180px;font-family:var(--mono);font-size:12px;color:var(--ink);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;
  padding:8px 12px;outline:none;transition:border-color .15s;
}}
.filter-search:focus{{border-color:var(--accent)}}
.filter-chips{{display:flex;flex-wrap:wrap;gap:6px}}
.filter-chip{{
  font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:.05em;
  color:var(--dim);background:var(--surface);border:1px solid var(--line);
  padding:4px 10px;border-radius:999px;cursor:pointer;transition:all .15s;
}}
.filter-chip:hover{{border-color:var(--accent);color:var(--accent)}}
.filter-chip.active{{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 12%,var(--surface));color:var(--accent)}}
.filter-chip.k-repo.active{{background:color-mix(in srgb,var(--accent) 18%,var(--surface));border-color:var(--accent)}}
.filter-chip.k-rel.active,.filter-chip.k-ph.active{{background:color-mix(in srgb,var(--ok) 18%,var(--surface));border-color:var(--ok)}}
.filter-chip.k-sec.active{{background:color-mix(in srgb,var(--bad) 18%,var(--surface));border-color:var(--bad)}}
.filter-chip.k-hn.active,.filter-chip.k-com.active{{background:color-mix(in srgb,var(--warn) 18%,var(--surface));border-color:var(--warn)}}
.filter-chip.k-new.active{{background:color-mix(in srgb,var(--ok) 18%,var(--surface));border-color:var(--ok)}}

/* ─── Export dropdown ─── */
.export-dropdown{{position:relative}}
.export-btn{{
  font-family:var(--mono);font-size:11px;font-weight:600;color:var(--dim);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;
  padding:6px 12px;cursor:pointer;transition:all .15s;
}}
.export-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.export-menu{{
  position:absolute;top:100%;inset-inline-end:0;z-index:30;min-width:180px;
  background:var(--surface);border:1px solid var(--line);border-radius:8px;
  box-shadow:0 12px 32px -8px rgba(0,0,0,.5);opacity:0;visibility:hidden;
  transform:translateY(-8px);transition:all .2s ease;padding:6px;
}}
.export-dropdown.open .export-menu{{opacity:1;visibility:visible;transform:translateY(0)}}
.export-item{{
  display:flex;align-items:center;gap:10px;width:100%;padding:8px 12px;border-radius:6px;
  color:var(--ink);font-size:12px;transition:background .15s;
}}
.export-item:hover{{background:var(--well)}}
.export-item svg{{width:16px;height:16px;color:var(--accent)}}

/* ─── Share button ─── */
.share-btn{{
  font-family:var(--mono);font-size:11px;font-weight:600;color:var(--dim);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;
  padding:6px 12px;cursor:pointer;transition:all .15s;
}}
.share-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.share-btn svg{{width:14px;height:14px;margin-inline-start:4px}}

/* ─── Reader mode button ─── */
.reader-toggle{{
  font-family:var(--mono);font-size:11px;font-weight:600;color:var(--dim);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;
  padding:6px 12px;cursor:pointer;transition:all .15s;
}}
.reader-toggle:hover{{border-color:var(--accent);color:var(--accent)}}
.reader-toggle.active{{background:var(--accent);border-color:var(--accent);color:#1a0a04}}

/* ─── Kind badges ─── */
.kind-badge{{
  font-family:var(--mono);font-size:9px;font-weight:600;letter-spacing:.08em;
  padding:2px 7px;border-radius:999px;display:inline-block;vertical-align:middle;
}}
.kind-badge.k-repo{{background:color-mix(in srgb,var(--accent) 18%,var(--surface));color:var(--accent);border:1px solid var(--accent)}}
.kind-badge.k-rel,.kind-badge.k-ph{{background:color-mix(in srgb,var(--ok) 18%,var(--surface));color:var(--ok);border:1px solid var(--ok)}}
.kind-badge.k-sec{{background:color-mix(in srgb,var(--bad) 18%,var(--surface));color:var(--bad);border:1px solid var(--bad)}}
.kind-badge.k-hn,.kind-badge.k-com{{background:color-mix(in srgb,var(--warn) 18%,var(--surface));color:var(--warn);border:1px solid var(--warn)}}
.kind-badge.k-new{{background:color-mix(in srgb,var(--ok) 18%,var(--surface));color:var(--ok);border:1px solid var(--ok);font-weight:800}}

/* ─── Hidden in reader mode ─── */
.reader-overlay .tools,
.reader-overlay .filter-bar,
.reader-overlay .toc,
.reader-overlay .story .cpy{{display:none!important}}

/* ─── Responsive ─── */
@media(max-width:520px){{
  .paper{{padding-top:48px}}
  .figure img{{max-height:230px}}
  .story .lnk{{max-width:100%}}
  .filter-bar{{flex-direction:column;align-items:stretch}}
  .filter-search{{width:100%}}
}}

/* ─── Print ─── */
@media print{{
  :root,html[data-theme="paper"],html[data-theme="ink"]{{
    --bg:#fff;--surface:#fff;--well:#fff;--line:#bbb;--linehi:#777;
    --ink:#000;--dim:#222;--faint:#555;--accent:#8a1d0d;--grain:0;
  }}
  #readbar,.tools,.filter-bar,.toc,.story .cpy,.reader-toggle,.export-dropdown,.share-btn,.reader-overlay{{display:none!important}}
  body{{background:#fff;font-size:12.5px}}
  .paper{{padding:0 0 20px}}
  .story,.tldr{{break-inside:avoid}}
  .figure img{{max-height:220px}}
  .story .lnk{{white-space:normal;word-break:break-all}}
  .masthead,.tldr,.toc,.reveal{{animation:none;opacity:1;transform:none}}
  .reader-overlay{{display:none!important}}
}}
</style>
</head>
<body>

<!-- Reading progress -->
<div id="readbar" aria-hidden="true"><i id="readfill"></i></div>

<!-- Floating tools -->
<div class="tools" aria-label="Tools">
  <button id="themeBtn" title="{{ui.theme}}" aria-label="{{ui.theme}}">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 3v18M12 3a9 9 0 0 1 0 18" fill="currentColor" stroke="none" opacity=".35"/></svg>
  </button>
  <button id="readerToggle" class="reader-toggle" title="{{ui.reader_mode}}" aria-label="{{ui.reader_mode}}" aria-pressed="false">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M4 20l16-16"/><path d="M2 12h7M15 12h7"/><path d="M9 8h1M9 16h1"/></svg>
    خواندن
  </button>
</div>

<article class="paper" x-data="reportApp()">
  <!-- Masthead -->
  <header class="masthead">
    <div class="kicker" x-html="kickerHtml"></div>
    <h1 x-text="reportTitle"></h1>
    <div class="byline"><b x-text="generatedAt"></b> · <b x-text="topic"></b></div>
    <div class="rule dbl"></div>
  </header>

  <!-- Filter/Search bar -->
  <div class="filter-bar" x-data="filterApp()">
    <input type="search" class="filter-search" placeholder="{{ui.search_placeholder}}" x-model="searchQuery" @input="filter()" aria-label="{{ui.search_placeholder}}">
    <div class="filter-chips">
      <template x-for="kind in kinds" :key="kind.key">
        <button type="button" class="filter-chip" :class="{{'k-'+kind.key: true, active: activeKinds.includes(kind.key)}}" @click="toggleKind(kind.key)" x-text="kind.label" :title="kind.title"></button>
      </template>
    </div>
    <div class="export-dropdown" x-data="{{ open: false }}">
      <button type="button" class="export-btn" @click="open = !open" aria-haspopup="true" aria-expanded="false" aria-label="{{ui.export_label}}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        {{ui.export_label}}
      </button>
      <div class="export-menu" x-show="open" @click.outside="open = false" x-transition>
        <button type="button" class="export-item" @click="exportTo('notion')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          Notion
        </button>
        <button type="button" class="export-item" @click="exportTo('obsidian')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 4v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4"/><path d="M14 12v8"/><path d="M10 16h4"/><path d="M12 12h.01"/></svg>
          Obsidian
        </button>
        <button type="button" class="export-item" @click="exportTo('markdown')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
          Markdown
        </button>
      </div>
    </div>
    <button type="button" class="share-btn" @click="shareReport()" aria-label="{{ui.share_label}}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51 15.42 17.49M15.41 6.51 8.59 10.49"/></svg>
      {{ui.share_label}}
    </button>
  </div>

  <!-- TL;DR -->
  <section class="tldr" x-show="tldr.length > 0">
    <h2 x-text="ui.tldr"></h2>
    <ol>
      <template x-for="(item, idx) in tldr" :key="idx">
        <li><i :data-idx="idx+1"></i><span x-text="item"></span></li>
      </template>
    </ol>
  </section>

  <section class="morning" x-show="morningStories.length > 0">
    <h2 x-text="ui.morning_brief"></h2>
    <div class="morning-list">
      <template x-for="story in morningStories" :key="story.url || story.title">
        <div class="morning-item">
          <span class="decision-pill" :class="'u-' + story.urgency" x-text="decisionLabels[story.action] || story.action"></span>
          <a :href="story.url" target="_blank" rel="noreferrer" x-text="story.title"></a>
        </div>
      </template>
    </div>
  </section>

  <!-- Table of Contents -->
  <nav class="toc" x-show="columns.length > 0" aria-label="{{ui.toc}}">
    <template x-for="(col, cIdx) in columns" :key="col.title">
      <a :href="'#col-' + cIdx" :class="{{on: activeToc === cIdx}}" @click.prevent="scrollToColumn(cIdx)">
        <i :data-num="cIdx+1"></i>
        <span x-text="col.title"></span>
      </a>
    </template>
  </nav>

  <!-- Columns -->
  <template x-for="(col, cIdx) in columns" :key="col.title">
    <div class="colhead" :id="'col-' + cIdx">
      <span class="n" x-text="cIdx + 1"></span>
      <h2 x-text="col.title"></h2>
      <span class="cnt mono" :data-count="col.news_list.length" x-text="ui.stories(count)"></span>
    </div>
    <div class="prologue" x-html="col.prologue" x-show="col.prologue"></div>

    <template x-for="(news, nIdx) in col.news_list" :key="news.url || nIdx">
      <div class="story reveal" :data-kind="news.kind" :data-column="cIdx">
        <div class="meta">
          <span class="k" :class="'k-' + news.kind" x-text="kindLabels[news.kind]"></span>
          <span class="src" x-text="news.source"></span>
          <span x-show="news.date" x-text="news.date"></span>
          <span class="kind-badge" :class="'k-' + news.kind" x-show="news.is_new" x-text="ui.new"></span>
        </div>
        <h3><a :href="news.url" target="_blank" rel="noreferrer" x-text="news.title"></a></h3>
        <div class="figure" x-show="news.image">
          <img :src="news.image" :alt="news.title" loading="lazy">
        </div>
        <div class="body" x-html="news.summary" x-show="news.summary"></div>
        <aside class="decision" x-show="news.action">
          <div class="decision-head"><b x-text="ui.decision"></b><span class="decision-pill" :class="'u-' + news.urgency" x-text="decisionLabels[news.action] || news.action"></span></div>
          <p dir="auto" x-text="news.action_reason"></p>
        </aside>
        <aside class="why" x-show="news.recommend_comment">
          <b x-text="ui.why_pick"></b>
          <p dir="auto" x-text="news.recommend_comment"></p>
        </aside>
        <div class="foot" x-show="news.url">
          <a class="lnk" :href="news.url" target="_blank" rel="noreferrer" x-text="news.url"></a>
          <button type="button" class="cpy" :data-title="news.title" :data-url="news.url" :data-copied="ui.copied" @click="copyUrl(news.url, news.title, $event)" x-text="ui.copy"></button>
        </div>
      </div>
    </template>
  </template>

  <!-- End mark -->
  <div class="endmark">— <span x-text="ui.end"></span> —</div>

  <!-- Footer -->
  <footer>
    <span x-text="generatedAt"></span> · <span x-text="modelLabel"></span> ·
    Powered by <a href="https://github.com/AgentEra/Agently">AGENTLY 4</a>
  </footer>
</article>

<!-- Reader mode overlay -->
<div class="reader-overlay" id="readerOverlay" aria-hidden="true" role="dialog" aria-label="{{ui.reader_mode_title}}">
  <header class="reader-header">
    <button type="button" class="iconbtn" @click="closeReader()" aria-label="{{ui.close_reader}}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
    </button>
    <div class="kicker" x-html="kickerHtml"></div>
    <h1 style="flex:1;font-size:clamp(22px,3.5vw,28px);font-family:var(--serif);font-weight:700;line-height:1.5;unicode-bidi:plaintext" x-text="reportTitle"></h1>
    <button type="button" class="iconbtn" @click="printReport()" aria-label="{{ui.print}}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V3h12v6"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="7"/></svg>
    </button>
  </header>
  <div class="reader-content" x-html="readerContent"></div>
</div>

<!-- Toast for copy/share feedback -->
<div id="toast" role="status" aria-live="polite"></div>

<!-- Alpine.js + htmx (loaded from local files) -->
<script src="/static/alpine.min.js" defer></script>
<script src="/static/htmx.min.js" defer></script>

<script>
/* ─── Language & UI labels ─── */
const UI_LABELS = {ui_labels_json};
const IS_RTL = {is_rtl};
const KIND_LABELS = {kind_labels_json};
const KIND_LABELS_FULL = {kind_labels_full_json};
const DECISION_LABELS = {decision_labels_json};

/* ─── Toast helper ─── */
function toast(message, good = true) {{
  const el = document.getElementById('toast');
  el.textContent = message;
  el.className = 'on ' + (good ? 'good' : 'err');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('on'), 3000);
}}

/* ─── Alpine: Filter App ─── */
function filterApp() {{
  return {{
    searchQuery: '',
    activeKinds: Object.keys(KIND_LABELS).filter(k => k !== 'web'), // default: all except generic web
    kinds: Object.entries(KIND_LABELS).map(([key, label]) => ({{key, label, title: KIND_LABELS_FULL[key] || label}})),
    filter() {{
      const q = this.searchQuery.toLowerCase();
      document.querySelectorAll('.story').forEach(story => {{
        const kind = story.dataset.kind || '';
        const title = story.querySelector('h3')?.textContent?.toLowerCase() || '';
        const summary = story.querySelector('.body')?.textContent?.toLowerCase() || '';
        const kindMatch = this.activeKinds.length === 0 || this.activeKinds.includes(kind);
        const textMatch = !q || title.includes(q) || summary.includes(q);
        story.style.display = (kindMatch && textMatch) ? '' : 'none';
      }});
      // Update column counts visible
      this.updateCounts();
    }},
    toggleKind(key) {{
      const idx = this.activeKinds.indexOf(key);
      if (idx >= 0) this.activeKinds.splice(idx, 1);
      else this.activeKinds.push(key);
      this.filter();
    }},
    updateCounts() {{
      document.querySelectorAll('.colhead').forEach(col => {{
        const cIdx = parseInt(col.id?.split('-')[1] || '0', 10);
        const stories = document.querySelectorAll(`.story[data-column="${{cIdx}}"]`);
        let visible = 0;
        stories.forEach(s => {{ if (s.style.display !== 'none') visible++; }});
        const cnt = col.querySelector('.cnt');
        if (cnt) cnt.textContent = UI_LABELS.stories(visible);
      }});
    }},
    init() {{
      this.filter();
    }}
  }}
}}

/* ─── Alpine: Report App ─── */
function reportApp() {{
  return {{
    reportTitle: {report_title_json},
    generatedAt: {generated_at_json},
    topic: {topic_json},
    language: {language_json},
    modelLabel: {model_label_json},
    tldr: {tldr_json},
    columns: {columns_json},
    kindLabels: KIND_LABELS,
    decisionLabels: DECISION_LABELS,
    ui: UI_LABELS,
    activeToc: 0,
    get morningStories() {{
      const priority = {{'ACT NOW': 0, PLAN: 1, EXPLORE: 2, MONITOR: 3, IGNORE: 4}};
      return this.columns.reduce((stories, column) => stories.concat(column.news_list || []), [])
        .sort((left, right) => (priority[left.action] ?? 9) - (priority[right.action] ?? 9))
        .slice(0, 5);
    }},
    get kickerHtml() {{
      return `${{IS_RTL ? '<div style="direction:rtl">' : ''}}<span style="font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;color:var(--faint);display:flex;gap:14px;flex-wrap:wrap;">${{this.generatedAt.split(' ')[0]}} ${{IS_RTL ? '·' : '·'}} <b style="color:var(--accent);font-weight:600">${{this.topic}}</b></span>${{IS_RTL ? '</div>' : ''}}`;
    }},
    scrollToColumn(idx) {{
      this.activeToc = idx;
      const el = document.getElementById('col-' + idx);
      if (el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }},
    copyUrl(url, title, ev) {{
      navigator.clipboard.writeText(url).then(() => {{
        const btn = ev.currentTarget;
        const oldText = btn.textContent;
        btn.textContent = UI_LABELS.copied;
        btn.classList.add('copied');
        setTimeout(() => {{ btn.textContent = oldText; btn.classList.remove('copied'); }}, 2000);
        toast(UI_LABELS.copied, true);
      }}).catch(() => toast('Copy failed', false));
    }},
    shareReport() {{
      if (navigator.share) {{
        navigator.share({{title: this.reportTitle, text: this.topic, url: window.location.href}})
          .then(() => toast('Shared', true))
          .catch(() => {{}});
      }} else {{
        // Fallback: generate share image via endpoint
        toast(UI_LABELS.share_pending, true);
        fetch('/api/share-image', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{report_title: this.reportTitle, topic: this.topic, tldr: this.tldr, columns: this.columns}})
        }}).then(r => r.json()).then(data => {{
          if (data.ok) {{
            const a = document.createElement('a');
            a.href = data.image_url;
            a.download = 'share-' + Date.now() + '.png';
            a.click();
            toast('Image ready', true);
          }} else {{
            toast(data.error || 'Share failed', false);
          }}
        }}).catch(() => toast('Share failed', false));
      }},
    exportTo(format) {{
      if (format === 'notion') {{
        // Open Notion export endpoint
        window.location.href = '/api/export/notion?report=' + encodeURIComponent(this.reportTitle);
      }} else if (format === 'obsidian') {{
        window.location.href = '/api/export/obsidian?report=' + encodeURIComponent(this.reportTitle);
      }} else if (format === 'markdown') {{
        window.location.href = '/api/export/markdown?report=' + encodeURIComponent(this.reportTitle);
      }}
      toast('Exporting to ' + format + '...', true);
    }},
    get readerContent() {{
      // Generate reader-mode content (simplified, no chrome)
      return this.columns.map(col => `
        <div class="colhead" style="margin-top:2rem">
          <span class="n">${{col.title}}</span>
        </div>
        ${{col.prologue ? '<div class="prologue">' + col.prologue + '</div>' : ''}}
        ${{col.news_list.map(n => `
          <div class="story">
            <div class="meta"><span class="k k-${{n.kind}}">${{KIND_LABELS[n.kind]}}</span><span class="src">${{n.source}}</span>${{n.date ? ' ' + n.date : ''}}</div>
            <h3><a href="${{n.url}}" target="_blank" rel="noreferrer">${{n.title}}</a></h3>
            ${{n.image ? '<div class="figure"><img src="' + n.image + '" alt="" loading="lazy"></div>' : ''}}
            ${{n.summary ? '<div class="body">' + n.summary + '</div>' : ''}}
            ${{n.action ? '<aside class="decision"><div class="decision-head"><b>' + UI_LABELS.decision + '</b><span class="decision-pill u-' + n.urgency + '">' + (DECISION_LABELS[n.action] || n.action) + '</span></div><p dir="auto">' + n.action_reason + '</p></aside>' : ''}}
            ${{n.recommend_comment ? '<aside class="why"><b>' + UI_LABELS.why_pick + '</b><p dir="auto">' + n.recommend_comment + '</p></aside>' : ''}}
            ${{n.url ? '<div class="foot"><a class="lnk" href="' + n.url + '" target="_blank" rel="noreferrer">' + n.url + ' ↗</a></div>' : ''}}
          </div>
        `).join('')}}
      `).join('');
    }},
    // Reader mode
    openReader() {{
      document.getElementById('readerOverlay').classList.add('open');
      document.body.style.overflow = 'hidden';
      document.getElementById('readerToggle').setAttribute('aria-pressed', 'true');
      document.getElementById('readerToggle').classList.add('active');
      document.getElementById('readerToggle').innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M4 20l16-16"/><path d="M2 12h7M15 12h7"/><path d="M9 8h1M9 16h1"/></svg> خروج';
    }},
    closeReader() {{
      document.getElementById('readerOverlay').classList.remove('open');
      document.body.style.overflow = '';
      document.getElementById('readerToggle').setAttribute('aria-pressed', 'false');
      document.getElementById('readerToggle').classList.remove('active');
      document.getElementById('readerToggle').innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M4 20l16-16"/><path d="M2 12h7M15 12h7"/><path d="M9 8h1M9 16h1"/></svg> خواندن';
    }},
    printReport() {{
      window.print();
    }},
    init() {{
      // Reading progress
      const fill = document.getElementById('readfill');
      window.addEventListener('scroll', () => {{
        const h = document.documentElement;
        const max = h.scrollHeight - h.clientHeight;
        if (fill) fill.style.width = (max > 0 ? Math.min(100, (h.scrollTop / max) * 100) : 0) + '%';
      }}, {{passive: true}});

      // Scroll reveal
      const observer = new IntersectionObserver((entries) => {{
        entries.forEach(e => {{ if (e.isIntersecting) e.target.classList.add('in'); }});
      }}, {{threshold: 0.1, rootMargin: '0px 0px -50px 0px'}});
      document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

      // TOC highlight on scroll
      const colHeads = document.querySelectorAll('.colhead');
      const tocLinks = document.querySelectorAll('.toc a');
      const tocObserver = new IntersectionObserver((entries) => {{
        entries.forEach(e => {{
          if (e.isIntersecting) {{
            const idx = parseInt(e.target.id?.split('-')[1] || '0', 10);
            this.activeToc = idx;
            tocLinks.forEach((l, i) => l.classList.toggle('on', i === idx));
          }}
        }});
      }}, {{threshold: 0.5, rootMargin: '-80px 0px -60% 0px'}});
      colHeads.forEach(h => tocObserver.observe(h));

      // Reader toggle
      const readerBtn = document.getElementById('readerToggle');
      readerBtn?.addEventListener('click', () => {{
        if (document.getElementById('readerOverlay').classList.contains('open')) {{
          this.closeReader();
        }} else {{
          this.openReader();
        }}
      }});

      // Keyboard: Escape closes reader
      document.addEventListener('keydown', (e) => {{
        if (e.key === 'Escape' && document.getElementById('readerOverlay').classList.contains('open')) {{
          this.closeReader();
        }}
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {{
          e.preventDefault();
          document.querySelector('.filter-search')?.focus();
        }}
      }});

      // Export dropdown click outside
      document.addEventListener('click', (e) => {{
        if (!e.target.closest('.export-dropdown')) {{
          document.querySelectorAll('.export-dropdown').forEach(d => d.open = false);
        }}
      }});

      // Initialize filter
      this.$refs?.filterApp?.filter?.();
    }},
    openReader() {{
      document.getElementById('readerOverlay').classList.add('open');
      document.body.style.overflow = 'hidden';
      document.getElementById('readerToggle').setAttribute('aria-pressed', 'true');
      document.getElementById('readerToggle').classList.add('active');
      document.getElementById('readerToggle').innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M4 20l16-16"/><path d="M2 12h7M15 12h7"/><path d="M9 8h1M9 16h1"/></svg> خروج';
    }},
    closeReader() {{
      document.getElementById('readerOverlay').classList.remove('open');
      document.body.style.overflow = '';
      document.getElementById('readerToggle').setAttribute('aria-pressed', 'false');
      document.getElementById('readerToggle').classList.remove('active');
      document.getElementById('readerToggle').innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l16 16M4 20l16-16"/><path d="M2 12h7M15 12h7"/><path d="M9 8h1M9 16h1"/></svg> خواندن';
    }}
  }}
}}

/* ─── Theme persistence ─── */
(function(){{
  var root = document.documentElement;
  var saved = null;
  try {{ saved = localStorage.getItem("ink-theme"); }} catch(e){{}}
  if (saved === "ink" || saved === "paper") root.dataset.theme = saved;
  var themeBtn = document.getElementById("themeBtn");
  if (themeBtn) themeBtn.addEventListener("click", function(){{
    var next = root.dataset.theme === "ink" ? "paper" : "ink";
    root.dataset.theme = next;
    try {{ localStorage.setItem("ink-theme", next); }} catch(e){{}}
  }});
}})();

/* ─── Export dropdown close on outside click ─── */
document.addEventListener('click', (e) => {{
  if (!e.target.closest('.export-dropdown')) {{
    document.querySelectorAll('.export-dropdown').forEach(d => d.open = false);
  }}
}});
</script>
</body>
</html>'''

print("Interactive report template created successfully!")
