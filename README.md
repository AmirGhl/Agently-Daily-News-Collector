# Agently Daily News Collector

> **AI-powered daily news briefings on any topic, in any language — with a local web control panel, a developer-focused pulse mode, weekly digests, Telegram delivery, an RSS feed, and hands-free daily publishing to GitHub Pages.**

Built on **[Agently](https://github.com/AgentEra/Agently) v4** (TriggerFlow workflows). Forked from [AgentEra/Agently-Daily-News-Collector](https://github.com/AgentEra/Agently-Daily-News-Collector) and heavily extended.

[中文文档](README_CN.md) · [Full Guide](docs/GUIDE.md) · [Releases](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases)

---

## Table of Contents

- [Highlights](#highlights)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Modes & Workflows](#modes--workflows)
- [Web Control Panel](#web-control-panel)
- [Configuration](#configuration)
- [Model Presets](#model-presets)
- [Delivery: Telegram & Webhook](#delivery-telegram--webhook)
- [Outputs & Dashboard](#outputs--dashboard)
- [Automated Daily Publishing](#automated-daily-publishing)
- [Build a Standalone Windows Executable](#build-a-standalone-windows-executable)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Important v3 → v4 Changes](#important-v3--v4-changes)
- [License](#license)

---

## Highlights

| Feature | Description |
|---------|-------------|
| 🖥️ **Web Control Panel** (`--ui`) | Run topics, schedule daily runs, browse the archive, edit settings — zero-build frontend in `webui/` |
| 🧑‍💻 **Developer Pulse** (`--dev`) | GitHub trending/releases/advisories, Hacker News, Reddit, Lobsters, dev.to, daily.dev, Product Hunt — with velocity badges & trend streaks |
| 📅 **Weekly Digest** (`--weekly`) | Synthesizes the last 7 days of reports into one narrative roundup |
| 🤖 **Telegram Bot** (`--bot`) | Two-way bot: send `/news <topic>`, `/dev`, `/weekly` and get the briefing back in the same chat |
| 📡 **RSS Feed** | `outputs/feed.xml` regenerates with every report |
| 🔁 **Model Fallback** | `MODEL.fallback_presets` retries the run on another provider (groq, openrouter, …) when the primary model fails |
| 🕵️ **Anti-Repeat History** | Stories already published are skipped (or kept and badged `NEW` vs repeat with `--allow-repeats`) |
| 📬 **Delivery** | Telegram channel-style posts or webhook JSON |
| ⚙️ **Fully Configurable** | Everything in [`SETTINGS.yaml`](SETTINGS.yaml); model presets for OpenAI, OpenRouter, Groq, DeepSeek, Together, Ollama |
| 🎨 **Redesigned Reports** | Editorial layout, sticky scrollspy navigation, kind badges (REPO/RELEASE/SECURITY), RTL support, dark/light mode, print styles, staggered motion (reduced-motion aware) |
| ♻️ **`--rerender`** | Re-render all existing reports' HTML/Markdown from their JSON with the current design — no LLM calls |

---

## Quick Start

### From Source (Python)

```bash
# 1. Clone and install
git clone https://github.com/AmirGhl/Agently-Daily-News-Collector.git
cd Agently-Daily-News-Collector
pip install -r requirements.txt

# 2. Add your LLM API key
echo DEEPSEEK_API_KEY=your_key_here > .env

# 3. Run
python app.py "AI agents"           # one-shot from terminal
python app.py --ui                  # web control panel
python app.py --dev                 # developer pulse
python app.py --weekly              # weekly digest
python app.py --bot                 # two-way Telegram bot
```

### Windows Standalone Executable (No Python Needed)

Download `DailyNewsCollector.exe` from [**Releases**](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases) → unzip → create a `.env` with your API key next to the exe → double-click (opens the web panel) or run from CLI:

```powershell
DailyNewsCollector.exe "AI agents" --quiet
DailyNewsCollector.exe --dev
DailyNewsCollector.exe --all
```

---

## CLI Reference

```bash
python app.py [topic ...] [options]
```

| Option | Meaning | Default |
|--------|---------|---------|
| `topic` (positional) | Topic to collect news about (words joined). If omitted and no flag given, you're prompted interactively. | — |
| `-s, --settings PATH` | Alternative settings file | `SETTINGS.yaml` |
| `-l, --language NAME` | Output language (any free-form name: English, Persian, Chinese, ...) | from settings |
| `-c, --max-columns N` | Max number of report columns | from settings |
| `-n, --max-news N` | Max stories per column | from settings |
| `-f, --formats ...` | Which files to save: `markdown json html` (markdown is always written) | from settings |
| `-o, --output-dir DIR` | Where to save reports | `outputs` |
| `-a, --all` | Generate a report for every topic under `TOPICS` | off |
| `--topics "a,b,c"` | Comma-separated topics to run in parallel and merge into one report | off |
| `--dev` | Developer Pulse mode (GitHub, HN, Reddit, …) | off |
| `--weekly` | Weekly digest of the last 7 days | off |
| `--rerender` | Re-render all existing reports from their JSON with current design (no LLM) | off |
| `--ui` | Open the local web control panel | off |
| `--port N` | Port for the web panel (probes up to 20 higher ports if busy) | `8899` |
| `--no-browser` | With `--ui`: start panel without opening a browser tab (autostart) | off |
| `--bot` | Run the two-way Telegram bot: replies to `/news`, `/dev`, `/weekly` | off |
| `--allow-repeats` | Keep stories that appeared in previous reports (badge fresh ones `NEW`) | off |
| `--no-tldr` | Skip the Key Takeaways summary | off |
| `--no-deliver` | Skip Telegram/webhook delivery for this run | off |
| `--quiet` | Print only saved file paths | off |
| `--debug` | Verbose logging | off |

**Examples**

```bash
# Multi-topic merge
python app.py --topics "AI agents,LLMs,AI coding" --formats markdown json html

# Persian report, 3 columns, 3 stories each, quiet
python app.py "AI agents" --language Persian --max-columns 3 --max-news 3 --quiet

# All configured topics at once
python app.py --all --quiet
```

---

## Modes & Workflows

### Standard Topic Mode (Default)

```
outline → search → pick → browse + summarize → write column → render report
```

- An LLM "chief editor" designs the report: column titles, requirements, and search keywords (or you provide a fixed outline via `OUTLINE.use_customized`).
- Each column searches (web + optional RSS), an LLM shortlists candidates, picked pages are browsed (Playwright / Jina Reader fallback) and summarized **concurrently**.
- Columns are written in parallel, the report gets LLM Key Takeaways, duplicates are removed across columns, and everything is rendered to Markdown / JSON / HTML.

### Developer Pulse (`--dev`)

Five fixed columns, **no web search, no LLM outline step**:

| Column | Sources |
|--------|---------|
| **Trending Repositories** | GitHub daily trending + GitHub Rising (repos gaining stars unusually fast in ~24–48h via OSS Insight) + GitHub search for repos created last week with fast-growing stars |
| **Fresh Releases** | New releases of your `watch_repos` — changelog summarized as "what changed / anything breaking / upgrade or wait" |
| **Security Watch** | Fresh high-severity GitHub Security Advisories for your `security_ecosystems` (pip, npm, go, rust, maven, nuget, rubygems, composer, pub) — affected versions, impact, concrete fix |
| **Hot Developer News** | Hacker News (Algolia API, falls back to hnrss.org) |
| **Product Radar** | Developer-relevant launches from today's Product Hunt front page |
| **Community Buzz** | Reddit top-of-day from configured subreddits + Lobsters hottest + dev.to top articles + daily.dev most-upvoted + custom `extra_feeds` |

- **Trend streaks**: repos trending multiple days in a row get flagged (🔥 trending N days) via persistent memory (`outputs/.trends.json`).
- **Your stack**: set `DEV_PULSE.stack` (e.g., `Python`, `React`) and summaries add a "what this means for you" sentence when genuinely relevant.
- All channels fetched in parallel; failures are skipped silently. Optional `GITHUB_TOKEN` in `.env` raises GitHub API limits from 60 to 5000 req/h.

### Weekly Digest (`--weekly`)

Reads the stored **JSON** of every report from the last 7 days, feeds a compact view of all their stories to a "chief editor" prompt ([`prompts/write_weekly.yaml`](prompts/write_weekly.yaml)), and produces one "Highlights of the Week" report: a 2–3 paragraph narrative overview plus 5–8 selected highlights, each linked back to its original story. Written through the same output pipeline (Markdown / JSON / HTML, index, dashboard, delivery).

### Two-Way Telegram Bot (`--bot`)

Run `python app.py --bot` (or enable in the web panel). The bot listens for messages from the configured `chat_id`:

- `/news <topic>` — generate a standard briefing
- `/dev` — generate Developer Pulse
- `/weekly` — generate weekly digest

Reports are delivered back to the same chat.

---

## Web Control Panel

```bash
python app.py --ui            # opens http://127.0.0.1:8899/
python app.py --ui --port 9000
```

**Double-clicking `DailyNewsCollector.exe` (no arguments) opens the panel automatically.**

The panel has exactly two pages:

### The Desk (Home)

- Start a run (topic, language, column/news counts, allow-repeats) with one line, or launch **Developer Pulse** / **Weekly digest** from quick links
- Reuse configured `TOPICS` as quick-fill links; press `/` to focus the input
- **Pipeline stage line** (سرفصل ← جست‌وجو ← گزینش ← خلاصه ← نگارش ← خروجی) lights up stage by stage, inferred from the live log, with a thin progress rule underneath; in Developer Pulse runs a row of **source-health chips** shows how many items each channel returned (or that it failed)
- **Wire line** always shows the latest log line; click to expand a compact terminal (auto-expands during a run)
- **Stats strip**: total reports, last-7-days count, current daily streak
- **Archive**: date-grouped, searchable newspaper index with kind filters (news / dev / weekly); hover a row for raw HTML/MD/JSON links
- **⚙ Settings modal** — model (provider, model id, API key, live connection test), report (language, tone, column/news counts, quick-topic list), Developer Pulse sources (subreddits, watched repos, extra RSS feeds, GitHub language), Telegram (bot token, channel, optional telegram-only proxy, live test-send), daily **scheduler** (dev/topic/weekly at HH:MM while the panel is open), and **Start with Windows** toggle (drops a silent `--ui --no-browser` launcher into the Startup folder)

### The Paper (Reader)

Click any archive row to read the report inside the panel:

- Key takeaways, column table-of-contents, numbered sections, full story summaries with REPO/RELEASE/SECURITY/LAUNCH tags, "why it was picked" margin notes, source links with one-click copy, reading-progress bar, font-size controls, print/PDF styling, estimated reading time, and a **send-to-Telegram** button for any archived report
- `Esc` returns to the desk
- Web-app manifest + icon included — install as a standalone window from the browser menu
- Ink/paper (dark/light) theme toggle in the header, persisted per browser

**Local API** (for scripting):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/state` | GET | Running flag, current topic, last report, model label, recent log lines |
| `/api/run` | POST | Start a run (`topic`, `dev`, `weekly`, `language`, `max_columns`, `max_news`, `allow_repeats`); `409` if already running |
| `/api/reports` | GET | Catalog of all generated reports |
| `/reports/<name>` | GET | Serve one report file (path-guarded to the output dir) |
| `/api/settings` | GET / POST | Read or save model/workflow settings (writes `settings.overrides.json` + `.env` key) |
| `/api/settings/test` | POST | Live connectivity check against the provider |

The panel binds to `127.0.0.1` only — not reachable from the network.

---

## Configuration

### SETTINGS.yaml Reference

All keys accept UPPERCASE or lowercase. `${VAR}` / `${ENV.VAR}` placeholders are resolved from the environment and `.env`.

| Section | Keys | What it controls |
|---------|------|------------------|
| `DEBUG` | `bool` | Verbose logging |
| `TOPICS` | `list[str]` | Topics used by `--all` |
| `PROXY` | `url` | Shared proxy for model / search / browse (each section can override) |
| `MODEL` | `preset` **or** `provider`, `base_url`, `model`, `model_type`, `auth.api_key`, `request_options` | LLM endpoint & sampling options (e.g. `temperature`, `extra_body`) |
| `SEARCH` | `max_results`, `timelimit` (`d`/`w`/`m`), `region` (e.g. `us-en`, `cn-zh`), `backend` (`auto`/`bing`/`duckduckgo`/`yahoo`/`google`/`yandex`/...), `rss_feeds`, `proxy` | Search engine behavior and extra RSS candidate pool |
| `BROWSE` | `enable_playwright`, `playwright_headless`, `enable_jina_fallback`, `response_mode` (`markdown`/`text`), `max_content_length`, `min_content_length`, `proxy` | Page fetching and content extraction |
| `WORKFLOW` | `max_column_num`, `max_news_per_column`, `output_language`, `tone` (`editorial`/`conversational`), `column_concurrency`, `summary_concurrency` | Report shape, voice, and parallelism |
| `OUTLINE` | `use_customized`, `customized.report_title`, `customized.column_list[]` (`column_title`, `column_requirement`, `search_keywords`) | Skip LLM outline generation and use a fixed outline |
| `OUTPUT` | `directory`, `formats` (`markdown`/`json`/`html`), `update_index`, `update_dashboard` | Where and how reports are saved |
| `SUMMARY` | `enable_tldr` | Key Takeaways block at the top of each report |
| `DEV_PULSE` | see [Developer Pulse mode](#developer-pulse-mode) | Sources and thresholds for `--dev` |
| `HISTORY` | `enabled`, `retention_days`, `path` | Freshness memory across runs |
| `DELIVERY` | `telegram.{enabled, bot_token, chat_id, send_html_file}`, `webhook.{enabled, url}` | Where finished reports get pushed |

The settings loader also keeps basic compatibility with old v3 keys (`MODEL_PROVIDER`, `MODEL_URL`, `MODEL_AUTH`, `MODEL_OPTIONS`, `MAX_COLUMN_NUM`, `USE_CUSTOMIZE_OUTLINE`).

### Model Presets

`MODEL.preset` expands to a full provider block — you only supply the API key:

| Preset | `.env` key | Default model |
|--------|------------|---------------|
| `openai` | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| `openrouter` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `together` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| `ollama` | — (local, no key) | `qwen2.5:7b` @ `localhost:11434` |

Set `AGENTLY_NEWS_MODEL` in `.env` (or `model:` in YAML) to override the preset's default model. Cloud presets fail fast with a clear error if the key is missing; `ollama` never needs one.

### Environment Variables (`.env`)

A local `.env` next to the project (or next to the exe) is loaded on start — existing environment variables are **never overridden**.

| Variable | Used for |
|----------|----------|
| `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `TOGETHER_API_KEY` | Per-preset API keys |
| `AGENTLY_NEWS_MODEL` | Override the preset's default model id |
| `CUSTOM_API_KEY` | API key for the panel's "custom" provider option |
| `GITHUB_TOKEN` | Optional — raises GitHub API limits in dev mode from 60 to 5000 req/h |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram delivery |
| `NEWS_WEBHOOK_URL` | Webhook delivery |
| `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL`, `DEEPSEEK_API_KEY` | Referenced by the sample `SETTINGS.yaml` advanced model block |

### settings.overrides.json

The web panel **never edits `SETTINGS.yaml`**. Instead it writes a sidecar `settings.overrides.json` next to it, which is overlaid onto the parsed YAML before env resolution — so your YAML comments and formatting survive. When an override sets `MODEL.preset`, the base `MODEL` block is replaced (keeping only `request_options`) so stale `base_url`/`auth` placeholders can't shadow the preset. Delete the file to fall back to pure `SETTINGS.yaml`.

---

## Delivery: Telegram & Webhook

### Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Find your chat id (e.g. message [@userinfobot](https://t.me/userinfobot)).
3. Add to `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHAT_ID=123456789
   ```
4. Set `DELIVERY.telegram.enabled: true` in `SETTINGS.yaml`. Each run then sends a compact digest message plus the standalone HTML report as an attachment (`send_html_file: false` to skip the attachment).

**Channel-style posts**: set `send_style: channel` — opening headlines post, then one post per story (with photo when available), then a closing stats post. `send_style: digest` keeps the old compact multi-story messages.

### Webhook

Set `NEWS_WEBHOOK_URL` in `.env` and `DELIVERY.webhook.enabled: true` — each finished report is POSTed as JSON (`title`, `takeaways`, `columns`, `markdown`) to that URL, ready for Slack/Discord bridges, n8n/Zapier flows, or your own service.

**Delivery failures are logged but never abort a run** — your report is always saved locally first.

---

## Outputs & Dashboard

Every run writes to `OUTPUT.directory` (default `./outputs`):

| File | Description |
|------|-------------|
| `<title>_<date>.md` | The Markdown report (always written) |
| `<title>_<date>.json` | Full structured data, used by `--rerender` and `--weekly` |
| `<title>_<date>.html` | Standalone styled page, no external dependencies |
| `INDEX.md` | Markdown index of all reports (`OUTPUT.update_index`) |
| `index.html` + `reports.json` | Browsable dashboard/catalog of all reports (`OUTPUT.update_dashboard`) |
| `.history.json` | Published-story memory for freshness (`HISTORY`, 30-day retention by default) |
| `.trends.json` | Trend-streak memory for Developer Pulse |
| `feed.xml` | RSS feed of all reports |

Because every report keeps its JSON, `python app.py --rerender` can rebuild all HTML/Markdown files with the current design at any time — instantly and without any LLM calls.

---

## Automated Daily Publishing

The repository includes GitHub Actions workflows (add them to your fork under `.github/workflows/`):

### `daily.yml` — Daily Developer Pulse + GitHub Pages

Runs the developer pulse every morning and publishes `outputs/` to **GitHub Pages** — dashboard, reports, and RSS feed included.

**To enable on your fork:**

1. Repo **Settings → Pages** → Source: **GitHub Actions**.
2. Repo **Settings → Secrets and variables → Actions** → add:
   - `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL`
   - (or edit `SETTINGS.yaml` to use a one-key `preset:` instead).
3. Wait for the schedule or run the workflow manually from the Actions tab.

### `release.yml` — Windows Executable Build

Tagging a release (`git tag v1.1.0 && git push --tags`) triggers the release workflow, which builds the Windows exe with PyInstaller and attaches it to the GitHub release automatically.

---

## Build a Standalone Windows Executable

Preferred — build from the shipped spec (already includes the hook fix and bundles `SETTINGS.yaml`, `prompts/`, and `webui/`):

```bash
pip install pyinstaller
pyinstaller DailyNewsCollector.spec --noconfirm
```

Or the equivalent explicit command:

```bash
pyinstaller --onefile --name DailyNewsCollector \
  --add-data "SETTINGS.yaml;." --add-data "prompts;prompts" \
  --add-data "webui;webui" \
  --collect-all agently --collect-all ddgs \
  --additional-hooks-dir packaging/hooks --noconfirm app.py
```

> `--additional-hooks-dir packaging/hooks` is required: it overrides a pyinstaller-hooks-contrib hook for an unrelated PyPI package called `workflow` that collides with this project's local `workflow` package.

The result is `dist/DailyNewsCollector.exe`. On first run it extracts a default `SETTINGS.yaml` and `prompts/` next to itself so you can edit them; `outputs/`, `logs/`, and history live next to the exe as well. Put a `.env` file next to the exe for model / Telegram credentials, then:

```powershell
DailyNewsCollector.exe                # double-click = opens the web panel
DailyNewsCollector.exe "AI agents" --quiet
DailyNewsCollector.exe --all          # every topic in TOPICS
DailyNewsCollector.exe --dev          # Developer Pulse
```

---

## Docker

A minimal [`Dockerfile`](Dockerfile) is included (Python 3.10 base, `pip install -r requirements.txt`, `CMD python app.py`):

```bash
docker build -t agently-news .
docker run --rm -it --env-file .env \
  -v "$PWD/outputs:/app/outputs" agently-news \
  python app.py "AI agents" --quiet
```

Mount `outputs/` to keep reports and history on the host. The image runs the CLI; it does not expose the panel port by default.

---

## Project Structure

```text
.
├── app.py                     # thin entry point -> news_collector.cli.main
├── SETTINGS.yaml              # all configuration (model, search, workflow, delivery, ...)
├── requirements.txt           # agently>=4.0.8.3, PyYAML, ddgs, beautifulsoup4, python-dotenv, httpx, jdatetime
├── Dockerfile
├── DailyNewsCollector.spec    # PyInstaller spec
├── news_collector/            # app / integration layer
│   ├── cli.py                 #   argparse CLI, frozen-exe handling, dispatch
│   ├── config.py              #   settings model, model presets, env resolution, overrides merge
│   ├── collector.py           #   DailyNewsCollector: wires model + tools + flow, runs collect(topic)
│   ├── dev_pulse.py           #   Developer Pulse outline + settings mutation
│   ├── weekly.py              #   weekly digest generation from stored report JSON
│   ├── history.py             #   freshness memory (.history.json)
│   ├── delivery.py            #   Telegram + webhook push
│   ├── markdown.py            #   Markdown rendering + localized labels
│   ├── html_report.py         #   standalone HTML report design
│   ├── dashboard.py           #   outputs/index.html catalog + reports.json
│   ├── rerender.py            #   --rerender implementation
│   ├── webui.py               #   local control-panel HTTP server + /api endpoints
│   ├── webui_html.py          #   inline fallback panel (used when webui/ is absent)
│   └── logging_utils.py       #   console + logs/collector.log
├── workflow/                  # TriggerFlow orchestration
│   ├── daily_news.py          #   parent flow + column sub flow + summary sub flow assembly
│   ├── report_chunks.py       #   request prep, outline, TL;DR, dedupe, write outputs, history
│   ├── column_chunks.py       #   per-column search / pick / write with fallbacks
│   ├── summary_chunks.py      #   browse + summarize per candidate, kind-specific prompt routing
│   └── common.py              #   chunk config, editor agents, tone/language helpers
├── tools/                     # pluggable adapter layer (see tools/README.md)
│   ├── base.py                #   Search/Browse protocols
│   ├── builtin.py             #   Agently v4 Search/Browse wrappers + Jina fallback
│   ├── rss.py                 #   RSS/Atom candidate pool
│   ├── dev_sources.py         #   GitHub/HN/Reddit/Lobsters/dev.to/daily.dev/Product Hunt channels + trend streaks
│   └── content_quality.py     #   invalid-content detection (captcha, paywalls, ...)
├── prompts/                   # structured prompt contracts (editable YAML)
│   ├── create_outline.yaml    #   design the report outline
│   ├── pick_news.yaml         #   shortlist candidates per column
│   ├── summarize_news.yaml    #   summarize a browsed article
│   ├── summarize_repo.yaml    #   introduce a GitHub repo conversationally
│   ├── summarize_release.yaml #   what changed / breaking / upgrade or wait
│   ├── summarize_advisory.yaml#   security advisory warning
│   ├── write_column.yaml      #   final column + prologue
│   ├── write_tldr.yaml        #   Key Takeaways
│   └── write_weekly.yaml      #   weekly digest overview + highlights
├── webui/                     # control panel — one self-contained HTML file, no build step
├── packaging/hooks/           # PyInstaller hook fix for the `workflow` name collision
├── outputs/                   # reports, dashboard, INDEX.md, .history.json, .trends.json
└── logs/                      # collector.log
```

---

## Architecture

The whole run is one Agently v4 `TriggerFlow` with two nested sub flows:

```
parent flow   prepare_request → generate_outline → for_each(column) → render_report
column flow   search → pick → summarize → write_column
summary flow  for_each(picked story) → browse → summarize   (concurrent fan-out)
```

### Agently v4 Features Used

| Feature | How It's Used Here |
|---------|-------------------|
| **TriggerFlow orchestration** | Replaces the old v3 workflow style with an explicit flow graph (`to`, `for_each`, `sub flow`, branching-ready composition). Runs columns concurrently and summarizes picked stories concurrently within each column. |
| **Sub flow composition** | "Build one column" is extracted into its own TriggerFlow and invoked repeatedly from the parent flow inside `for_each(column)`. Parent stays focused on report-level orchestration; child can be tested, visualized, and exported independently. Future variants (briefing column, deep-dive column, regional column) can reuse or derive from the child flow. |
| **Structured output contracts** | YAML prompts define output schema directly for outline generation, news picking, summarizing, and column writing. Much less handwritten parsing glue, clearer interfaces between steps, easier prompt iteration. |
| **Built-in Search / Browse tools** | Defaults to Agently v4 built-in tool implementations instead of the old project-local helpers. Users can still swap implementations through `./tools` without rewriting the workflow. |
| **Runtime resources & state namespaces** | TriggerFlow runtime resources inject logger/search/browse dependencies; runtime state stores execution data (request, outline, intermediate results). Dependency wiring and execution state are separated cleanly, keeping chunk code thinner. |
| **Environment-aware settings** | Agently v4 `set_settings(..., auto_load_env=True)` works directly with `${ENV.xxx}` placeholders. Model endpoint, model name, and API key can be switched by environment instead of editing code or committing secrets. |

### Overall Effect

- Core product behavior remains familiar to v3 users, but the project now has a cleaner `app/workflow/tools/prompts` split.
- More logic is expressed in Agently-native capabilities instead of project-specific glue code.
- True concurrency is now part of the default execution model (v3 was effectively serial).
- Replacing tools, adjusting prompts, or evolving workflow steps is lower-risk than in the old v3 layout.
- Workflow evolution can happen by layer: report-level changes stay in the parent flow, column-level changes stay in the sub flow instead of forcing both to change together.

---

## Important v3 → v4 Changes

The business chain is still roughly:

```
outline → search → pick → browse + summarize → write column → render markdown
```

What changed is the engineering shape around that chain.

### Project-Level Changes

- The old v3 project used a main workflow plus a nested column workflow under `./workflows`, with custom `search.py` / `browse.py` helpers and storage-style state passing.
- The v4 project separates responsibilities more clearly:
  - `news_collector/`: app/integration layer
  - `workflow/`: parent flow, column sub flow, and concrete chunk logic
  - `tools/`: search/browse adapter layer
  - `prompts/`: structured prompt contracts
- Model configuration is no longer hardcoded in Python. It now uses `${ENV.xxx}` placeholders from `SETTINGS.yaml`, so deployment and local switching are simpler.
- Tool wiring is no longer buried inside workflow code. Search, browse, and logger are injected as TriggerFlow runtime resources, which makes the workflow easier to replace or test.
- The workflow plan is now closer to the business boundary:
  - parent flow: `prepare_request → generate_outline → for_each(column) → render_report`
  - column sub flow: `search → pick → summarize → write_column`
  - the `summarize` stage inside the column flow is further pushed down into a summary sub flow, where TriggerFlow handles fan-out and collection directly instead of leaving `asyncio.gather` in business code
  - this keeps the parent focused on report orchestration and the child focused on one column lifecycle
  - the immediate value of `sub flow` here is that the column pipeline becomes a reusable, independently evolvable workflow unit instead of staying buried inside one oversized parent chunk

---

## Notes

- Python `>=3.10` is required because Agently v4 requires it.
- This project requires Agently `>=4.0.8.3`.
- Model settings use `${ENV.xxx}` placeholders resolved from the environment / `.env` (Agently v4 `auto_load_env=True`), or the simpler `MODEL.preset` shortcut.
- `tools/` defaults to Agently v4 built-in implementations, but you can replace the factories there with your own tools (see [`tools/README.md`](tools/README.md)).
- `workflow/` is split by business boundary into the parent flow, the column sub flow, report-level chunks, and column-level chunks.
- `news_collector/` acts as the app/integration layer for configuration, model wiring, CLI, web panel, rendering, and delivery.
- The sample [`SETTINGS.yaml`](SETTINGS.yaml) ships with `BROWSE.enable_playwright: false` and `enable_jina_fallback: true`; enable Playwright for better browse quality on dynamic or protected news sites (`pip install playwright && playwright install chromium`).
- The interactive CLI prompt is bilingual (English/Chinese); the web panel UI is Persian/RTL-first; reports themselves follow `WORKFLOW.output_language`.
- A Chinese README for the original project is available at [`README_CN.md`](README_CN.md) (may lag behind this file).

---

## License

[Apache 2.0](LICENSE)