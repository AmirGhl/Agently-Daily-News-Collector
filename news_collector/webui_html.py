from __future__ import annotations

# Single-file control panel served by webui.py. Everything inline so the
# PyInstaller build needs no extra data files.
# Design language: «اتاق فرمان» / Night Ops — dark glass command center.
# Ember-orange signature glow + neon lime signal, Vazirmatn UI + JetBrains
# Mono data, dot-grid atmosphere, CSS-only motion (transform/opacity,
# reduced-motion aware).

PAGE_HTML = """<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>سردبیر — اتاق فرمان خبر</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0a0b0f; --bg-2:#0d0f15; --card:#12141c; --card-2:#171a24;
  --border:#232735; --border-hi:#323848;
  --text:#e9ebf2; --dim:#8b91a3; --faint:#565d70;
  --accent:#ff6a3d; --accent-2:#ffb35c; --lime:#d4ff4f;
  --ok:#3ddc97; --danger:#ff4d5e; --gold:#ffb35c;
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
  font-family:"Vazirmatn",Tahoma,sans-serif; background:var(--bg); color:var(--text);
  min-height:100vh; line-height:1.75; font-size:14.5px;
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
.wrap{max-width:1280px; margin:0 auto; padding:0 clamp(14px,3.5vw,40px) 90px}
button{font-family:inherit}
.mono{font-family:var(--mono)}

/* ================= motion ================= */
@keyframes rise{from{opacity:0; transform:translateY(16px)} to{opacity:1; transform:none}}
@keyframes card-in{from{opacity:0; transform:translateY(12px) scale(.98)} to{opacity:1; transform:none}}
@keyframes pulse{50%{opacity:.2; transform:scale(.6)}}
@keyframes blink{0%,55%{opacity:1} 56%,100%{opacity:0}}
@keyframes scan{from{transform:translateY(-100%)} to{transform:translateY(420%)}}
@keyframes spin-slow{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none !important; transition:none !important}
}

/* ================= app bar ================= */
.appbar{
  position:sticky; top:0; z-index:15; display:flex; align-items:center; gap:14px;
  padding:14px 2px 12px; margin-bottom:26px;
  background:linear-gradient(color-mix(in srgb, var(--bg) 88%, transparent), transparent);
  backdrop-filter:blur(14px); animation:rise .5s var(--spring) both;
}
.logo{display:flex; align-items:center; gap:11px; text-decoration:none; color:inherit}
.logo .mark{
  width:38px; height:38px; border-radius:10px; background:var(--grad);
  display:grid; place-items:center; color:#14060144; box-shadow:var(--glow-soft);
  font-family:var(--mono); font-weight:800; font-size:17px; color:#1a0a04;
}
.logo b{font-size:19px; font-weight:900; letter-spacing:-.01em}
.logo small{
  display:block; font-family:var(--mono); font-size:8.5px; letter-spacing:.34em;
  color:var(--faint); text-transform:uppercase; line-height:1; margin-top:2px;
}
.appbar .spacer{flex:1}
.chip-model{
  font-family:var(--mono); font-size:11px; color:var(--dim); direction:ltr;
  border:1px solid var(--border); border-radius:8px; padding:7px 12px;
  background:var(--card); white-space:nowrap; max-width:280px; overflow:hidden; text-overflow:ellipsis;
}
.status{
  display:inline-flex; align-items:center; gap:8px; font-size:12px; font-weight:700;
  border:1px solid var(--border); border-radius:8px; background:var(--card);
  padding:7px 14px; min-height:36px; transition:border-color .3s, color .3s, box-shadow .3s;
}
.status .lamp{width:8px; height:8px; border-radius:50%; background:var(--ok); box-shadow:0 0 10px var(--ok)}
.status.busy{border-color:var(--accent); color:var(--accent-2); box-shadow:var(--glow)}
.status.busy .lamp{background:var(--accent); box-shadow:0 0 12px var(--accent); animation:pulse 1.1s ease-in-out infinite}
.gear{
  width:38px; height:38px; display:grid; place-items:center; cursor:pointer;
  background:var(--card); border:1px solid var(--border); border-radius:10px;
  color:var(--dim); transition:color .2s, border-color .2s, box-shadow .2s, transform .55s var(--spring);
}
.gear:hover{color:var(--accent); border-color:var(--accent); box-shadow:var(--glow); transform:rotate(100deg)}
.gear:active{transform:rotate(100deg) scale(.9)}
.gear svg{width:19px; height:19px; stroke:currentColor; fill:none; stroke-width:1.8}

/* ================= hero ================= */
.hero{display:flex; align-items:flex-end; justify-content:space-between; gap:18px; flex-wrap:wrap; animation:rise .55s .06s var(--spring) both}
.hero h1{font-size:clamp(1.7rem,4vw,2.5rem); font-weight:900; line-height:1.25; letter-spacing:-.02em}
.hero h1 em{
  font-style:normal; background:var(--grad);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
}
.hero .sub{font-size:12.5px; color:var(--dim); margin-top:2px}
.hero .sub b{font-family:var(--mono); font-weight:600; color:var(--lime)}
.stats{display:flex; gap:10px}
.stat{
  min-width:104px; background:var(--card); border:1px solid var(--border); border-radius:14px;
  padding:12px 16px 9px; position:relative; overflow:hidden;
  transition:border-color .2s, transform .2s var(--spring), box-shadow .2s;
}
.stat:hover{transform:translateY(-2px); border-color:var(--border-hi); box-shadow:var(--shadow)}
.stat::before{
  content:""; position:absolute; top:0; inset-inline:0; height:2px;
  background:var(--grad); opacity:.7;
}
.stat b{
  display:block; font-family:var(--mono); font-weight:800; font-size:1.7rem;
  line-height:1.2; color:var(--text);
}
.stat span{font-size:10.5px; color:var(--dim); font-weight:500}
@media (max-width:640px){.stats{width:100%; justify-content:space-between} .stat{flex:1; min-width:0}}

/* ================= layout ================= */
.cols{display:grid; grid-template-columns:370px 1fr; gap:clamp(16px,2.5vw,28px); margin-top:28px}
@media (max-width:940px){.cols{grid-template-columns:1fr}}
aside{animation:rise .55s .12s var(--spring) both; display:flex; flex-direction:column; gap:16px}
main{animation:rise .55s .2s var(--spring) both}

.panel{
  background:var(--card); border:1px solid var(--border); border-radius:16px;
  padding:20px 20px 22px; position:relative;
  transition:border-color .25s;
}
.panel:focus-within{border-color:var(--border-hi)}
.panel h2{
  font-size:13px; font-weight:900; letter-spacing:.02em; margin-bottom:14px;
  display:flex; align-items:center; gap:10px; color:var(--text);
}
.panel h2 .tag{
  font-family:var(--mono); font-size:8.5px; font-weight:600; letter-spacing:.3em;
  color:var(--faint); text-transform:uppercase; margin-inline-start:auto;
}

label{display:block; font-size:11px; font-weight:700; color:var(--dim); margin:13px 0 6px}
input[type=text],input[type=password],select{
  width:100%; font:inherit; font-size:13.5px; color:var(--text);
  background:var(--bg-2); border:1px solid var(--border); border-radius:10px;
  padding:10px 13px; outline:none; min-height:44px;
  transition:border-color .18s, box-shadow .18s;
}
input:focus,select:focus{border-color:var(--accent); box-shadow:0 0 0 3px rgba(255,106,61,.15)}
input::placeholder{color:var(--faint)}
select{appearance:none; background-image:linear-gradient(45deg, transparent 49%, var(--dim) 50%, transparent 60%); background-size:9px 9px; background-position:left 13px center; background-repeat:no-repeat}
.row2{display:grid; grid-template-columns:1fr 1fr; gap:10px}
.chips{display:flex; flex-wrap:wrap; gap:6px; margin-top:9px}
.chip{
  font:inherit; font-size:11.5px; cursor:pointer; color:var(--dim);
  background:var(--bg-2); border:1px solid var(--border); padding:5px 13px; border-radius:999px;
  min-height:30px; transition:all .18s var(--spring);
}
.chip:hover{border-color:var(--accent); color:var(--accent-2); transform:translateY(-1px); box-shadow:var(--glow)}
.chip:active{transform:scale(.94)}
.check{display:flex; align-items:center; gap:9px; margin-top:15px; font-size:12.5px; color:var(--dim); cursor:pointer; min-height:24px}
.check input{accent-color:var(--accent); width:16px; height:16px}

.go{
  margin-top:18px; width:100%; font-size:14.5px; font-weight:900; cursor:pointer;
  color:#1a0a04; background:var(--grad); border:none; border-radius:12px;
  padding:13px; min-height:48px; box-shadow:var(--glow-soft);
  transition:filter .18s, transform .12s var(--spring), box-shadow .2s;
}
.go:hover:not(:disabled){filter:brightness(1.12); box-shadow:var(--glow)}
.go:active:not(:disabled){transform:scale(.97)}
.go:disabled{opacity:.4; cursor:wait; box-shadow:none}
.go>span{position:relative}

/* quick action tiles */
.actions{display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px}
.tile{
  position:relative; text-align:start; cursor:pointer; border-radius:12px; padding:13px 14px 11px;
  background:var(--bg-2); border:1px solid var(--border); color:var(--text); overflow:hidden;
  transition:border-color .2s, transform .18s var(--spring), box-shadow .2s;
}
.tile:hover:not(:disabled){transform:translateY(-2px); border-color:var(--accent); box-shadow:var(--glow)}
.tile:active:not(:disabled){transform:scale(.97)}
.tile:disabled{opacity:.4; cursor:wait}
.tile .t-ico{
  font-family:var(--mono); font-size:15px; font-weight:800; line-height:1;
  color:var(--lime); margin-bottom:6px; display:block;
}
.tile b{display:block; font-size:12.5px; font-weight:800}
.tile small{display:block; font-size:10px; color:var(--dim); line-height:1.7; margin-top:1px}

/* ================= terminal ================= */
.telex{border:1px solid var(--border); border-radius:14px; background:#07080c; overflow:hidden; position:relative}
@media (prefers-color-scheme: light){.telex{background:#12141c}}
.telex::after{
  content:""; position:absolute; inset-inline:0; top:0; height:26%;
  background:linear-gradient(rgba(212,255,79,.05), transparent); pointer-events:none;
  animation:scan 7s linear infinite;
}
.telex-bar{
  display:flex; align-items:center; gap:7px; padding:9px 13px;
  border-bottom:1px solid #1a1d28;
}
.telex-bar i{width:9px; height:9px; border-radius:50%; background:#252a38}
.telex-bar i:first-child{background:var(--accent); box-shadow:0 0 8px var(--accent)}
.telex-bar em{
  font-style:normal; margin-inline-start:auto; font-family:var(--mono);
  font-size:8.5px; letter-spacing:.32em; color:var(--faint); text-transform:uppercase;
}
.console{
  direction:ltr; text-align:left; color:#c9cfa6;
  font-family:var(--mono); font-size:11px; line-height:1.85; height:230px; overflow-y:auto;
  padding:12px 14px 4px; white-space:pre-wrap; word-break:break-all;
}
.console::-webkit-scrollbar{width:8px}
.console::-webkit-scrollbar-thumb{background:#252a38; border-radius:4px}
.console .hint{color:var(--faint)}
.cursorline{
  direction:ltr; text-align:left; padding:0 14px 11px;
  font-family:var(--mono); font-size:11px; color:#c9cfa6;
}
.cursorline::before{content:"$ "; color:var(--lime)}
.cursorline::after{content:"▮"; animation:blink 1.1s steps(1) infinite; color:var(--accent)}

/* ================= archive ================= */
.toolbar{display:flex; gap:12px; align-items:center; justify-content:space-between; flex-wrap:wrap; margin-bottom:16px}
.toolbar h2{font-size:17px; font-weight:900}
.toolbar .count{font-family:var(--mono); color:var(--lime); font-size:11.5px; font-weight:600}
.search{max-width:280px; flex:1; min-height:42px !important; border-radius:10px}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(256px,1fr)); gap:14px}
.card{
  background:var(--card); border:1px solid var(--border); border-radius:16px;
  padding:17px 18px 12px; display:flex; flex-direction:column; gap:7px;
  position:relative; cursor:pointer; overflow:hidden;
  transition:transform .22s var(--spring), box-shadow .25s, border-color .25s;
  animation:card-in .45s var(--spring) both; animation-delay:calc(min(var(--i,0),12)*45ms);
}
.card::before{
  content:""; position:absolute; top:0; inset-inline:0; height:2px;
  background:var(--grad); opacity:0; transition:opacity .25s;
}
.card:hover{transform:translateY(-4px); box-shadow:var(--shadow), var(--glow-soft); border-color:var(--border-hi)}
.card:hover::before{opacity:1}
.card:active{transform:translateY(-2px) scale(.99)}
.card .topic{
  font-family:var(--mono); font-size:9px; font-weight:600; letter-spacing:.22em;
  text-transform:uppercase; color:var(--accent-2);
}
.card h3{font-size:14.5px; font-weight:800; line-height:1.55; unicode-bidi:plaintext; text-align:start}
.card .meta{
  font-family:var(--mono); font-size:10px; color:var(--faint);
  margin-top:auto; padding-top:8px; direction:ltr; text-align:left;
}
.card .links{display:flex; gap:6px; border-top:1px solid var(--border); margin-top:8px; padding-top:10px}
.card .links a{
  font-family:var(--mono); font-size:10px; font-weight:600; color:var(--dim); text-decoration:none;
  border:1px solid var(--border); border-radius:7px; padding:4px 10px; min-height:26px;
  display:inline-flex; align-items:center; transition:all .15s;
}
.card .links a:hover{color:var(--accent-2); border-color:var(--accent); box-shadow:var(--glow)}
.empty{
  border:1px dashed var(--border-hi); border-radius:16px; padding:70px 20px;
  text-align:center; color:var(--dim);
}
.empty .orn{font-family:var(--mono); font-size:2.2rem; color:var(--faint); line-height:1}
.empty b{display:block; font-size:1.4rem; font-weight:900; color:var(--text); margin:10px 0 4px}

/* ================= toast ================= */
#toast{
  position:fixed; bottom:24px; left:24px; z-index:40; max-width:360px;
  background:var(--card-2); border:1px solid var(--border-hi); border-radius:12px;
  border-inline-start:3px solid var(--accent);
  padding:13px 18px; font-size:13px; box-shadow:var(--shadow);
  opacity:0; transform:translateY(12px) scale(.97); transition:all .3s var(--spring); pointer-events:none;
}
#toast.show{opacity:1; transform:none}
#toast.good{border-inline-start-color:var(--ok)}

/* ================= settings sheet ================= */
#scrim{
  position:fixed; inset:0; z-index:20; background:rgba(4,5,8,.68);
  backdrop-filter:blur(5px); opacity:0; pointer-events:none; transition:opacity .25s;
}
#scrim.open{opacity:1; pointer-events:auto}
#sheet{
  position:fixed; z-index:21; top:50%; left:50%; width:min(640px, calc(100vw - 24px));
  max-height:min(88vh, 800px); overflow-y:auto;
  background:var(--card); border:1px solid var(--border-hi); border-radius:20px;
  box-shadow:0 40px 100px -24px rgba(0,0,0,.85), var(--glow-soft);
  padding:26px 26px 24px; opacity:0; pointer-events:none;
  transform:translate(-50%,-45%) scale(.95);
  transition:opacity .24s, transform .32s var(--spring);
}
#sheet.open{opacity:1; pointer-events:auto; transform:translate(-50%,-50%)}
#sheet h2{
  font-size:17px; font-weight:900; margin-bottom:2px;
  display:flex; align-items:center; justify-content:space-between;
}
#sheet .sub{font-size:11.5px; color:var(--dim); margin-bottom:16px}
#sheet .close{
  background:none; border:none; cursor:pointer; color:var(--dim);
  font-size:24px; line-height:1; padding:4px 10px; border-radius:8px;
  transition:color .15s, transform .2s var(--spring);
}
#sheet .close:hover{color:var(--accent); transform:rotate(90deg)}
.providers{display:grid; grid-template-columns:repeat(auto-fill,minmax(118px,1fr)); gap:9px; margin-bottom:4px}
.provider{
  position:relative; border:1px solid var(--border); border-radius:12px; background:var(--bg-2);
  cursor:pointer; padding:11px 13px 9px;
  transition:border-color .18s, transform .18s var(--spring), box-shadow .18s;
}
.provider:hover{transform:translateY(-2px); border-color:var(--border-hi)}
.provider:active{transform:scale(.96)}
.provider input{position:absolute; opacity:0; pointer-events:none}
.provider .p-name{font-family:var(--mono); font-size:12.5px; font-weight:800; direction:ltr; text-align:left}
.provider .p-hint{font-size:10px; color:var(--dim); direction:ltr; text-align:left}
.provider.sel{border-color:var(--accent); box-shadow:var(--glow), inset 0 0 0 1px var(--accent)}
.provider.sel::after{
  content:"●"; position:absolute; top:8px; inset-inline-end:10px;
  color:var(--accent); font-size:9px;
}
.keywrap{position:relative}
.keywrap input{direction:ltr; padding-inline-end:66px; font-family:var(--mono); font-size:12px}
.keywrap .eye{
  position:absolute; inset-inline-end:9px; top:50%; transform:translateY(-50%);
  font-size:11px; font-weight:700; color:var(--dim);
  background:none; border:none; cursor:pointer; padding:7px; min-height:32px;
}
.keywrap .eye:hover{color:var(--accent-2)}
.keyhint{font-family:var(--mono); font-size:10px; color:var(--dim); margin-top:6px; direction:ltr; text-align:left}
.keyhint b{color:var(--ok)}
.sheet-actions{display:flex; gap:10px; margin-top:22px}
.sheet-actions .go{margin-top:0; flex:1}
.sheet-actions .go.alt{
  flex:0 0 auto; padding-inline:20px; background:var(--bg-2); color:var(--text);
  border:1px solid var(--border-hi); box-shadow:none;
}
.sheet-actions .go.alt:hover:not(:disabled){border-color:var(--accent); color:var(--accent-2); box-shadow:var(--glow); filter:none}
#testResult{font-family:var(--mono); font-size:11px; margin-top:10px; min-height:18px; direction:ltr; text-align:left}
#testResult.ok{color:var(--ok)}
#testResult.bad{color:var(--danger)}

footer{
  margin-top:70px; text-align:center;
  font-family:var(--mono); font-size:10px; letter-spacing:.18em; color:var(--faint);
}
footer a{color:var(--accent-2); text-decoration:none}
</style>
</head>
<body>
<div class="wrap">

<div class="appbar">
  <a class="logo" href="/">
    <span class="mark">▞</span>
    <span><b>سردبیر</b><small>NEWS OPS</small></span>
  </a>
  <span class="spacer"></span>
  <span class="chip-model" id="model">…</span>
  <span class="status" id="status"><span class="lamp"></span><span id="statusText">آماده</span></span>
  <button class="gear" id="gearBtn" title="تنظیمات" aria-label="تنظیمات">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
  </button>
</div>

<div class="hero">
  <div>
    <h1>امروز چه خبر، <em>قربان؟</em></h1>
    <div class="sub"><span id="today"></span> · <b id="clock"></b></div>
  </div>
  <div class="stats">
    <div class="stat"><b id="statTotal">0</b><span>گزارش در بایگانی</span></div>
    <div class="stat"><b id="statToday">0</b><span>گزارش امروز</span></div>
    <div class="stat"><b id="statTopics">0</b><span>موضوع متفاوت</span></div>
  </div>
</div>

<div class="cols">
  <aside>
    <section class="panel">
      <h2>مأموریت جدید<span class="tag">NEW RUN</span></h2>
      <form id="runForm">
        <label for="topic">موضوع</label>
        <input type="text" id="topic" placeholder="مثلاً: AI agents" autocomplete="off">
        <div class="chips" id="topicChips"></div>
        <label for="language">زبان گزارش</label>
        <select id="language">
          <option value="">پیش‌فرض تنظیمات</option>
          <option>English</option>
          <option>Persian</option>
          <option>Chinese</option>
          <option>Arabic</option>
        </select>
        <div class="row2">
          <div>
            <label for="maxColumns">تعداد ستون</label>
            <select id="maxColumns">
              <option value="">پیش‌فرض</option>
              <option>1</option><option>2</option><option>3</option><option>4</option>
            </select>
          </div>
          <div>
            <label for="maxNews">خبر در هر ستون</label>
            <select id="maxNews">
              <option value="">پیش‌فرض</option>
              <option>1</option><option>2</option><option>3</option><option>4</option><option>5</option>
            </select>
          </div>
        </div>
        <label class="check"><input type="checkbox" id="allowRepeats">اجازهٔ تکرار خبرهای گزارش‌های قبلی</label>
        <button class="go" id="goBtn" type="submit"><span>تولید گزارش</span></button>
        <div class="actions">
          <button class="tile" id="devBtn" type="button">
            <span class="t-ico">⌁</span><b>نبض برنامه‌نویسی</b>
            <small>GitHub · HN · Reddit · Lobsters</small>
          </button>
          <button class="tile" id="weeklyBtn" type="button">
            <span class="t-ico">⟳</span><b>جمع‌بندی هفتگی</b>
            <small>خلاصهٔ ۷ روز گذشته</small>
          </button>
        </div>
      </form>
    </section>

    <section class="panel">
      <h2>سیم خبر<span class="tag">LIVE WIRE</span></h2>
      <div class="telex">
        <div class="telex-bar"><i></i><i></i><i></i><em>TELEX · LIVE</em></div>
        <div class="console" id="console"><span class="hint">در انتظار نخستین اجرا…</span></div>
        <div class="cursorline"></div>
      </div>
    </section>
  </aside>

  <main>
    <div class="toolbar">
      <h2>بایگانی <span class="count" id="count"></span></h2>
      <input type="text" class="search" id="search" placeholder="جستجو در عنوان و موضوع…">
    </div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty" hidden>
      <div class="orn">[ ]</div>
      <b>هنوز گزارشی نیست</b>
      اولین موضوع را وارد کن و «تولید گزارش» را بزن.
    </div>
  </main>
</div>

<footer>NEWS OPS CONSOLE · Powered by <a href="https://github.com/AgentEra/Agently">AGENTLY 4</a></footer>
</div>

<div id="toast"></div>

<div id="scrim"></div>
<div id="sheet" role="dialog" aria-modal="true" aria-label="تنظیمات">
  <h2>تنظیمات هوش مصنوعی<button class="close" id="sheetClose" aria-label="بستن">×</button></h2>
  <div class="sub">مدل و سرویس‌دهنده را انتخاب کن؛ کلید در فایل .env کنار برنامه ذخیره می‌شود.</div>

  <label>سرویس‌دهنده</label>
  <div class="providers" id="providers"></div>

  <label for="setModel">مدل <span style="font-weight:400">(خالی = پیش‌فرض سرویس)</span></label>
  <input type="text" id="setModel" placeholder="مثلاً llama-3.3-70b-versatile" style="direction:ltr" autocomplete="off">

  <div id="baseUrlRow" hidden>
    <label for="setBaseUrl">Base URL</label>
    <input type="text" id="setBaseUrl" placeholder="https://api.example.com/v1" style="direction:ltr" autocomplete="off">
  </div>

  <div id="keyRow">
    <label for="setKey">API Key</label>
    <div class="keywrap">
      <input type="password" id="setKey" placeholder="sk-..." autocomplete="off">
      <button type="button" class="eye" id="keyEye">نمایش</button>
    </div>
    <div class="keyhint" id="keyHint"></div>
  </div>

  <div class="row2">
    <div>
      <label for="setLanguage">زبان گزارش</label>
      <select id="setLanguage">
        <option>English</option><option>Persian</option><option>Chinese</option><option>Arabic</option>
      </select>
    </div>
    <div>
      <label for="setTone">لحن</label>
      <select id="setTone">
        <option value="editorial">رسمی (سردبیری)</option>
        <option value="conversational">محاوره‌ای</option>
      </select>
    </div>
  </div>

  <div class="sheet-actions">
    <button class="go" id="saveSettings" type="button"><span>ذخیره تنظیمات</span></button>
    <button class="go alt" id="testSettings" type="button"><span>تست اتصال</span></button>
  </div>
  <div id="testResult"></div>
</div>

<script>
const $ = (id) => document.getElementById(id);
let wasRunning = false, reports = [];
const faNum = (n) => Number(n).toLocaleString("fa-IR");

$("today").textContent = new Date().toLocaleDateString("fa-IR",
  {weekday:"long", year:"numeric", month:"long", day:"numeric"});
function tick(){
  $("clock").textContent = new Date().toLocaleTimeString("fa-IR",
    {hour:"2-digit", minute:"2-digit", second:"2-digit"});
}
tick(); setInterval(tick, 1000);

function toast(message, good){
  const el = $("toast");
  el.textContent = message;
  el.className = good ? "good show" : "show";
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 4200);
}

/* ---------- count-up ---------- */
function countUp(el, target){
  const start = performance.now(), from = 0, dur = 700;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches){ el.textContent = faNum(target); return; }
  function frame(t){
    const p = Math.min((t - start) / dur, 1);
    el.textContent = faNum(Math.round(from + (target - from) * (1 - Math.pow(1 - p, 3))));
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function renderStats(){
  const today = new Date().toISOString().slice(0, 10);
  countUp($("statTotal"), reports.length);
  countUp($("statToday"), reports.filter(r => (r.date || "") === today).length);
  countUp($("statTopics"), new Set(reports.map(r => r.topic || "")).size);
}

/* ---------- state ---------- */
function renderState(s){
  const busy = s.running;
  $("status").className = "status" + (busy ? " busy" : "");
  $("statusText").textContent = busy ? ("در حال تولید: " + s.topic) : "آماده";
  $("goBtn").disabled = busy;
  $("devBtn").disabled = busy;
  $("weeklyBtn").disabled = busy;
  $("goBtn").querySelector("span").textContent = busy ? "در حال اجرا…" : "تولید گزارش";
  if (s.model) $("model").textContent = s.model;
  if (s.log && s.log.length){
    const box = $("console");
    const stick = box.scrollTop + box.clientHeight >= box.scrollHeight - 30;
    box.textContent = s.log.join("\\n");
    if (stick) box.scrollTop = box.scrollHeight;
  }
  if (!$("topicChips").childElementCount && s.topics && s.topics.length){
    for (const t of s.topics){
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = t;
      b.onclick = () => { $("topic").value = t; };
      $("topicChips").appendChild(b);
    }
  }
  if (wasRunning && !busy){
    loadReports();
    if (s.error) toast("اجرا با خطا متوقف شد: " + s.error);
    else toast("گزارش آماده شد: " + (s.last_report || ""), true);
  }
  wasRunning = busy;
}

async function poll(){
  try{
    const s = await (await fetch("/api/state")).json();
    renderState(s);
    setTimeout(poll, s.running ? 1200 : 4000);
  }catch(e){ setTimeout(poll, 4000); }
}

/* ---------- archive ---------- */
function renderReports(){
  const q = $("search").value.trim().toLowerCase();
  const list = q ? reports.filter(r =>
    (r.report_title || "").toLowerCase().includes(q) ||
    (r.topic || "").toLowerCase().includes(q)) : reports;
  $("count").textContent = list.length ? faNum(list.length) + " REC" : "";
  $("empty").hidden = list.length > 0;
  const grid = $("grid");
  grid.innerHTML = "";
  for (const r of list){
    const files = r.files || {};
    const primary = files.html || files.markdown;
    const card = document.createElement("article");
    card.className = "card";
    card.style.setProperty("--i", grid.childElementCount);
    card.innerHTML =
      '<div class="topic"></div><h3></h3>' +
      '<div class="meta"></div><div class="links"></div>';
    card.querySelector(".topic").textContent = r.topic || "";
    card.querySelector("h3").textContent = r.report_title || "بدون عنوان";
    card.querySelector(".meta").textContent =
      (r.date || "") + (r.language ? "  ·  " + r.language : "");
    const links = card.querySelector(".links");
    for (const [fmt, label] of [["html","VIEW"],["markdown","MD"],["json","JSON"]]){
      if (!files[fmt]) continue;
      const a = document.createElement("a");
      a.href = "/reports/" + encodeURIComponent(files[fmt]);
      a.target = "_blank"; a.textContent = label;
      links.appendChild(a);
    }
    if (primary){
      card.addEventListener("click", (ev) => {
        if (ev.target.tagName !== "A")
          window.open("/reports/" + encodeURIComponent(primary), "_blank");
      });
    }
    grid.appendChild(card);
  }
  renderStats();
}

async function loadReports(){
  try{
    reports = await (await fetch("/api/reports")).json();
    renderReports();
  }catch(e){}
}

$("search").addEventListener("input", renderReports);

/* ---------- runs ---------- */
async function startRun(body, label){
  const res = await fetch("/api/run", {
    method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
  const out = await res.json();
  if (out.ok){ toast("اجرا شروع شد: " + label, true); $("console").textContent = ""; }
  else if (out.message === "already_running") toast("یک اجرا در جریان است؛ صبر کنید.");
  else toast("شروع اجرا ناموفق بود.");
}

function formOptions(){
  return {
    language: $("language").value || null,
    max_columns: $("maxColumns").value ? parseInt($("maxColumns").value) : null,
    max_news: $("maxNews").value ? parseInt($("maxNews").value) : null,
    allow_repeats: $("allowRepeats").checked,
  };
}

$("runForm").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const topic = $("topic").value.trim();
  if (!topic){ toast("موضوع را وارد کنید."); $("topic").focus(); return; }
  startRun({topic, ...formOptions()}, topic);
});

$("devBtn").addEventListener("click", () => {
  startRun({dev:true, ...formOptions()}, "نبض برنامه‌نویسی");
});

$("weeklyBtn").addEventListener("click", () => {
  startRun({weekly:true, language: $("language").value || null}, "جمع‌بندی هفتگی");
});

/* ---------- settings sheet ---------- */
const PROVIDER_NAMES = {
  ollama:"Ollama", groq:"Groq", openrouter:"OpenRouter",
  openai:"OpenAI", deepseek:"DeepSeek", together:"Together", custom:"Custom",
};
const PROVIDER_HINTS = {
  ollama:"محلی — بدون کلید", groq:"خیلی سریع", openrouter:"همهٔ مدل‌ها",
  openai:"GPT", deepseek:"DeepSeek", together:"متن‌باز", custom:"آدرس دلخواه",
};
let settingsData = null, selectedPreset = "";

function selectProvider(id){
  selectedPreset = id;
  document.querySelectorAll(".provider").forEach(el =>
    el.classList.toggle("sel", el.dataset.id === id));
  $("baseUrlRow").hidden = id !== "custom";
  $("keyRow").style.display = id === "ollama" ? "none" : "";
  const preset = (settingsData?.presets || []).find(p => p.id === id);
  $("setModel").placeholder = preset ? preset.default_model : "model-id";
  const env = id === "custom" ? "CUSTOM_API_KEY" : (preset ? preset.key_env : "");
  const saved = settingsData?.current?.key_env === env && settingsData?.current?.key_present;
  $("keyHint").innerHTML = env
    ? ("→ .env : " + env + (saved ? " — <b>saved key found</b>" : ""))
    : "";
}

async function openSheet(){
  try{ settingsData = await (await fetch("/api/settings")).json(); }
  catch(e){ toast("خواندن تنظیمات ناموفق بود."); return; }
  const box = $("providers");
  box.innerHTML = "";
  const ids = [...settingsData.presets.map(p => p.id), "custom"];
  for (const id of ids){
    const el = document.createElement("label");
    el.className = "provider"; el.dataset.id = id;
    el.innerHTML = '<input type="radio" name="prov"><div class="p-name"></div><div class="p-hint"></div>';
    el.querySelector(".p-name").textContent = PROVIDER_NAMES[id] || id;
    el.querySelector(".p-hint").textContent = PROVIDER_HINTS[id] || "";
    el.addEventListener("click", () => selectProvider(id));
    box.appendChild(el);
  }
  const cur = settingsData.current || {};
  selectProvider(cur.preset || (cur.base_url && cur.base_url.includes("localhost") ? "ollama" : "custom"));
  $("setModel").value = cur.model && !cur.model.includes("${") ? cur.model : "";
  $("setBaseUrl").value = cur.base_url && !cur.base_url.includes("${") ? cur.base_url : "";
  $("setLanguage").value = cur.language || "English";
  $("setTone").value = cur.tone || "editorial";
  $("setKey").value = "";
  $("testResult").textContent = ""; $("testResult").className = "";
  $("scrim").classList.add("open"); $("sheet").classList.add("open");
}
function closeSheet(){
  $("scrim").classList.remove("open"); $("sheet").classList.remove("open");
}
$("gearBtn").addEventListener("click", openSheet);
$("sheetClose").addEventListener("click", closeSheet);
$("scrim").addEventListener("click", closeSheet);
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closeSheet(); });
$("keyEye").addEventListener("click", () => {
  const inp = $("setKey");
  inp.type = inp.type === "password" ? "text" : "password";
  $("keyEye").textContent = inp.type === "password" ? "نمایش" : "پنهان";
});

function settingsPayload(){
  return {
    preset: selectedPreset,
    model: $("setModel").value.trim() || null,
    base_url: $("setBaseUrl").value.trim() || null,
    api_key: $("setKey").value.trim() || null,
    language: $("setLanguage").value,
    tone: $("setTone").value,
  };
}

$("saveSettings").addEventListener("click", async () => {
  const res = await fetch("/api/settings", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify(settingsPayload())});
  const out = await res.json();
  if (out.ok){ toast("تنظیمات ذخیره شد ✓", true); closeSheet(); }
  else toast("ذخیره ناموفق: " + (out.message || ""));
});

$("testSettings").addEventListener("click", async () => {
  const el = $("testResult");
  el.className = ""; el.textContent = "testing…";
  try{
    const res = await fetch("/api/settings/test", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify(settingsPayload())});
    const out = await res.json();
    if (out.ok){
      el.className = "ok";
      el.textContent = "✓ connected" + (out.models != null ? " — " + out.models + " models" : "");
    } else {
      el.className = "bad";
      el.textContent = "✗ " + (out.message || "failed");
    }
  }catch(e){ el.className = "bad"; el.textContent = "✗ request failed"; }
});

poll();
loadReports();
</script>
</body>
</html>
"""

__all__ = ["PAGE_HTML"]
