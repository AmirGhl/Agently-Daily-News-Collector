# Daily News Collector

**AI-powered daily news briefings on any topic, in any language — with a beautiful local web UI, developer pulse mode, weekly digests, Telegram delivery, and automated GitHub Pages publishing.**

[English](README.md) · [فارسی](README_FA.md) · [中文](README_CN.md) · [Releases](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌐 **Web UI** | Modern Persian/RTL-first control panel — run topics, schedule daily runs, browse archive, edit settings, test connections |
| 🧑‍💻 **Developer Pulse** | GitHub trending/releases/security, Hacker News, Reddit, Lobsters, dev.to, daily.dev, Product Hunt — velocity badges & trend streaks |
| 📅 **Weekly Digest** | Synthesizes last 7 days into a narrative roundup with highlights |
| 🤖 **Telegram Bot** | Two-way: send `/news <topic>`, `/dev`, `/weekly` → get briefing back in chat |
| 📡 **RSS Feed** | Auto-generated `outputs/feed.xml` with every report |
| 🔁 **Model Fallback** | Auto-retries on Groq/OpenRouter/Ollama when primary fails |
| 🕵️ **Anti-Repeat** | Remembers published URLs (30 days) — skips repeats or badges `NEW` |
| 🎨 **Beautiful Reports** | Editorial layout, sticky TOC, dark/light mode, RTL support, print-ready |
| ♻️ **Re-render** | `--rerender` rebuilds all HTML/MD from JSON instantly — no LLM calls |

---

## 🚀 Quick Start

### Option 1: Windows Exe (No Python Needed)
1. Download `DailyNewsCollector.exe` from [**Releases**](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases)
2. Create `.env` next to the exe:
   ```dotenv
   DEEPSEEK_API_KEY=your_key_here
   ```
3. **Double-click** → Web UI opens at `http://127.0.0.1:8899`

### Option 2: From Source (Python 3.10+)
```bash
git clone https://github.com/AmirGhl/Agently-Daily-News-Collector.git
cd Agently-Daily-News-Collector
pip install -r requirements.txt
echo DEEPSEEK_API_KEY=your_key_here > .env

# Run from terminal
python app.py "AI agents"           # one-shot report
python app.py --ui                  # open web UI
python app.py --dev                 # developer pulse
python app.py --weekly              # weekly digest
python app.py --bot                 # Telegram bot
```

---

## 🖥️ Web UI — Main Way to Use It

```bash
python app.py --ui          # opens http://127.0.0.1:8899
# or just double-click the .exe
```

**Two pages, zero build step:**

### 📋 The Desk (Home)
- **One-line run**: type a topic, pick language, columns, stories — hit Enter
- **Quick actions**: Developer Pulse, Weekly Digest buttons
- **Live pipeline**: visual stage line (Outline → Search → Pick → Summarize → Write → Output) with progress bar
- **Source health chips** (dev mode): shows items per channel (GitHub, HN, Reddit…)
- **Terminal wire**: last log line, click to expand full console
- **Archive**: date-grouped, searchable, filter by type (news/dev/weekly)
- **Settings modal (⚙)**: Model (preset + API key + live test), Report (language, tone, counts), Dev Pulse sources, Telegram (token, chat, test send), Daily Scheduler (HH:MM while panel open), **Start with Windows** toggle
- **Dark/Light** theme toggle (persisted)

### 📖 The Paper (Reader)
Click any archive row → clean reading view:
- Key Takeaways (numbered)
- Sticky column TOC with scroll-spy
- Full summaries with REPO/RELEASE/SECURITY badges
- "Why it mattered" margin notes
- Source links with one-click copy
- Reading progress bar, font size, print/PDF, estimated read time
- **Send to Telegram** button per archived report
- `Esc` to return

---

## 🎯 Modes

| Command | What It Does |
|---------|--------------|
| `python app.py "topic"` | Standard briefing: LLM outlines columns → searches → picks → browses → summarizes → renders |
| `--dev` | **Developer Pulse** — 6 fixed columns, no web search, no outline step. GitHub trending/rising/new + releases + security advisories + HN + Product Hunt + Reddit/Lobsters/dev.to/daily.dev + custom RSS |
| `--weekly` | Reads last 7 days of JSON reports → writes narrative "Highlights of the Week" |
| `--bot` | Telegram bot: replies to `/news <topic>`, `/dev`, `/weekly` from your `chat_id` |
| `--all` | Runs every topic in `TOPICS` list (from SETTINGS.yaml) |
| `--topics "a,b,c"` | Runs multiple topics in parallel, merges into one report |
| `--rerender` | Rebuilds all HTML/Markdown from existing JSON — instant, no LLM |

---

## ⚙️ Configuration

Everything in **`SETTINGS.yaml`** (or via the Web UI ⚙ modal — writes `settings.overrides.json`, never touches your YAML).

### Minimal Setup (Model Presets)
```yaml
MODEL:
  preset: deepseek      # or: openai, openrouter, groq, together, ollama
```
Add the matching key to `.env`:
```dotenv
DEEPSEEK_API_KEY=sk-...
# or OPENAI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, TOGETHER_API_KEY
# ollama needs no key (runs locally at localhost:11434)
```

### Key Sections
| Section | Controls |
|---------|----------|
| `MODEL` | Provider, model, temperature, fallback presets |
| `SEARCH` | Engine, region, time limit, RSS feeds |
| `BROWSE` | Playwright on/off, Jina fallback, content length |
| `WORKFLOW` | Max columns, stories/column, language, tone, concurrency |
| `OUTLINE` | Fixed outline (skip LLM editor) |
| `OUTPUT` | Formats (md/json/html), dashboard, index, RSS |
| `DEV_PULSE` | Subreddits, watched repos, extra feeds, GitHub language, stack |
| `HISTORY` | Retention days, filter repeats |
| `DELIVERY` | Telegram (channel/digest style, HTML attachment), Webhook |

**Environment variables** (`.env` next to project or exe) — never committed:
```dotenv
# Model keys (pick one preset's key)
DEEPSEEK_API_KEY=...
# GROQ_API_KEY=...
# OPENAI_API_KEY=...

# Optional
GITHUB_TOKEN=ghp_...          # raises GitHub API limit 60→5000/hr
TELEGRAM_BOT_TOKEN=123:ABC    # for delivery + bot
TELEGRAM_CHAT_ID=123456789
NEWS_WEBHOOK_URL=https://...  # Slack/Discord/n8n/etc
```

---

## 📦 Outputs

Every run writes to `outputs/` (configurable):

| File | Purpose |
|------|---------|
| `Title_YYYY-MM-DD.md` | Markdown report |
| `Title_YYYY-MM-DD.json` | Structured data (used by `--weekly`, `--rerender`) |
| `Title_YYYY-MM-DD.html` | Standalone styled page (works offline) |
| `index.html` + `reports.json` | **Browsable dashboard** — open in browser |
| `INDEX.md` | Markdown index of all reports |
| `feed.xml` | RSS feed |
| `.history.json` | Published URL memory (anti-repeat) |
| `.trends.json` | Dev Pulse trend streaks |

---

## 🤖 Telegram Delivery

1. Create bot via [@BotFather](https://t.me/BotFather) → copy token
2. Get chat ID via [@userinfobot](https://t.me/userinfobot)
3. Add to `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHAT_ID=123456789
   ```
4. Enable in `SETTINGS.yaml`:
   ```yaml
   DELIVERY:
     telegram:
       enabled: true
       send_style: channel    # or "digest"
       send_html_file: true
   ```

**Channel style**: headlines post → one post per story (with photo) → stats post.  
**Digest style**: compact multi-story messages.

---

## 🔄 Automated Daily Publishing (GitHub Pages)

The repo includes **`.github/workflows/daily.yml`** — runs Developer Pulse every morning, publishes `outputs/` to GitHub Pages (dashboard + reports + RSS).

**Enable on your fork:**
1. **Settings → Pages** → Source: **GitHub Actions**
2. **Settings → Secrets → Actions** → add:
   - `DEEPSEEK_API_KEY` (or your preset's key)
   - `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL` (if not using preset)
3. Done — runs daily at 08:00 UTC, or trigger manually from Actions tab.

---

## 🐳 Docker

```bash
docker build -t daily-news .
docker run --rm -it --env-file .env \
  -v "$PWD/outputs:/app/outputs" daily-news \
  python app.py "AI agents" --quiet
```

---

## 🛠 Build Windows Exe Yourself

```bash
pip install pyinstaller
pyinstaller DailyNewsCollector.spec --noconfirm
# → dist/DailyNewsCollector.exe
```

---

## 📁 Project Structure (Simplified)

```
.
├── app.py                  # entry point
├── SETTINGS.yaml           # all config
├── requirements.txt
├── DailyNewsCollector.spec # PyInstaller spec
├── news_collector/         # app layer
│   ├── cli.py              # commands, dispatch
│   ├── config.py           # settings model, presets
│   ├── collector.py        # wires model + tools + flow
│   ├── dev_pulse.py        # dev mode outline
│   ├── weekly.py           # weekly digest
│   ├── webui.py            # web UI server + API
│   ├── html_report.py      # report design
│   ├── dashboard.py        # index.html catalog
│   └── ...
├── workflow/               # TriggerFlow orchestration
│   ├── daily_news.py       # parent + column + summary flows
│   └── ...
├── tools/                  # pluggable search/browse adapters
├── prompts/                # YAML prompt contracts
├── webui/                  # single-file HTML UI (HTMX + Alpine)
├── outputs/                # generated reports
└── logs/
```

---

## 🧠 Architecture (Brief)

Built on **Agently v4 TriggerFlow** — explicit flow graph with sub-flows:

```
Parent Flow:     prepare → outline → for_each(column) → render
Column Sub-flow: search → pick → summarize → write
Summary Sub-flow: for_each(story) → browse → summarize  (parallel)
```

- **True concurrency**: columns + per-column summaries run in parallel
- **Sub-flows**: column pipeline is reusable, testable, independently evolvable
- **Structured prompts**: YAML defines output schemas — no parsing glue code
- **Runtime resources**: logger/search/browse injected, not hardcoded
- **Env-aware settings**: `${ENV.xxx}` placeholders resolved at load

---

## 📝 License

[Apache 2.0](LICENSE)