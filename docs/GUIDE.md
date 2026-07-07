# Agently Daily News Collector v4

Type a topic — get a designed, multi-column news briefing: searched, shortlisted, browsed, summarized, and assembled by LLM agents, saved as Markdown / JSON / a styled standalone HTML page, and optionally pushed straight to your Telegram.

Agently Daily News Collector has been rewritten on top of **Agently v4** and now uses:

- `TriggerFlow` for the end-to-end pipeline
- Agently v4 built-in `Search` and `Browse` tools
- structured output contracts instead of the old v3 workflow API

> Version constraint: this project requires **Agently v4.0.8.3 or newer**. The current implementation uses `TriggerFlow sub flow` to organize per-column pipelines, so earlier v4 releases are not compatible with the workflow structure used here.

The previous Agently v3 project has been removed from this repo; it remains available in the upstream repository.

## Table of contents

- [How it works](#how-it-works)
- [Features](#features)
- [Quick Start](#quick-start)
- [CLI reference](#cli-reference)
- [Configuration](#configuration)
  - [SETTINGS.yaml reference](#settingsyaml-reference)
  - [Model presets](#model-presets)
  - [Environment variables (.env)](#environment-variables-env)
  - [settings.overrides.json](#settingsoverridesjson)
- [Web control panel](#web-control-panel)
- [Developer Pulse mode](#developer-pulse-mode)
- [Weekly digest](#weekly-digest)
- [RSS feed sources](#rss-feed-sources)
- [Multiple topics in one run](#multiple-topics-in-one-run)
- [Delivery: Telegram & webhook](#delivery-telegram--webhook)
- [Outputs, dashboard, history](#outputs-dashboard-history)
- [Report design](#report-design)
- [Frontend development (zero-build)](#frontend-development-zero-build)
- [Build a standalone Windows executable](#build-a-standalone-windows-executable)
- [Docker](#docker)
- [Run it every day automatically](#run-it-every-day-automatically)
- [Project structure](#project-structure)
- [Important v3 -> v4 changes](#important-v3---v4-changes)
- [Notes](#notes)

## How it works

The whole run is one Agently v4 `TriggerFlow` with two nested sub flows:

```text
parent flow   prepare_request -> generate_outline -> for_each(column) -> render_report
column flow   search -> pick -> summarize -> write_column
summary flow  for_each(picked story) -> browse -> summarize   (concurrent fan-out)
```

1. **Outline** — an LLM "chief editor" designs the report: column titles, requirements, and search keywords (or you provide a fixed outline via `OUTLINE.use_customized`).
2. **Search** — each column queries the search engine (plus optional RSS feeds and, in dev mode, developer channels) with several query variants.
3. **Pick** — an LLM shortlists the most relevant candidates per column.
4. **Summarize** — picked pages are browsed (Playwright / Jina Reader fallback) and summarized concurrently; GitHub repos, releases, and security advisories get their own dedicated prompts.
5. **Write & render** — each column gets a written prologue, the report gets LLM Key Takeaways, duplicates are removed across columns, and everything is rendered to Markdown / JSON / HTML, indexed, remembered in history, and delivered.

## Features

- Input a topic and generate a multi-column news briefing automatically
- Search, shortlist, browse, summarize, and assemble stories in one flow
- **Key Takeaways (TL;DR)**: an LLM-written executive summary at the top of every report (`SUMMARY.enable_tldr`)
- **Freshness memory**: published story URLs are remembered (`outputs/.history.json`), so tomorrow's run skips stories that already appeared in earlier reports (`HISTORY`, `--allow-repeats` to bypass); duplicate stories are also removed across columns within one report
- **Delivery**: push each finished report to a Telegram chat (message + HTML attachment) and/or POST it to any webhook (`DELIVERY`)
- **RSS sources**: optional RSS/Atom feeds act as an extra, rate-limit-free candidate pool next to the search engine (`SEARCH.rss_feeds`)
- **Multi-topic runs**: list topics under `TOPICS` and generate every briefing in one command with `--all`
- **Standalone Windows executable**: build a single `DailyNewsCollector.exe` with PyInstaller — no Python required on the target machine
- **Web control panel**: `--ui` opens a local control panel in the browser (double-clicking the exe opens it automatically) — a deliberately minimal **two-page, zero-build panel** (one hand-written HTML file, no Node.js anywhere): a *desk* page (topic input, dev-pulse/weekly shortcuts, live pipeline stage line, collapsible log, date-grouped searchable archive, inline AI settings) and a *reader* page that renders any report's JSON as a clean newspaper-style article with a reading-progress bar; ink/paper (dark/light) theme toggle included
- **Developer Pulse mode** (`--dev` or the panel's dev button): skips web search entirely and pulls straight from GitHub trending + new-and-rising repos, GitHub releases & security advisories, Hacker News, Reddit, Lobsters, dev.to, daily.dev, Product Hunt, and any custom RSS/Atom feeds (`extra_feeds` — bridge X/Twitter via RSSHub, blogs, newsletters); GitHub repos are introduced conversationally from their README + metadata (what it is, how it works, where you'd use it, why it's trending)
- **Weekly digest** (`--weekly` or the panel button): synthesizes the last 7 days of reports into one narrative roundup with the week's top highlights
- **Trend streaks**: repos trending multiple days in a row get flagged (🔥 trending N days) using a persistent trend memory (`outputs/.trends.json`)
- **Tone control**: `WORKFLOW.tone: editorial | conversational` applies to all summaries, columns, and takeaways (dev mode defaults to conversational)
- **Model presets**: `MODEL.preset: openai | openrouter | groq | deepseek | together | ollama` — one word plus the matching API key in `.env` and you're done
- **In-panel AI settings**: the ⚙ button in the web panel opens an inline settings section — pick the provider, paste the API key (stored in `.env`), set model/language/tone, and hit "Test connection" for a live check; choices are saved to `settings.overrides.json` so `SETTINGS.yaml` and its comments stay untouched
- **Zero-build frontend**: the whole panel is one self-contained file at [`./webui/index.html`](./webui/index.html) (vanilla HTML/CSS/JS, RTL-first) — edit it, refresh the browser, done; no npm, no bundler, nothing to install
- **Redesigned report pages**: editorial layout with sticky scrollspy column navigation, kind badges (REPO / RELEASE / SECURITY), numbered takeaways, staggered entrance motion (reduced-motion aware), Lora + Vazirmatn typography with offline fallbacks, correct mixed RTL/LTR text (`dir=auto` + `unicode-bidi: plaintext`), automatic dark/light mode, and print styles
- **`--rerender`**: instantly re-render every existing report's HTML/Markdown from its JSON with the current design — no LLM, design updates apply retroactively
- Save the final report as Markdown, JSON, and/or a styled standalone HTML page under `./outputs` (`OUTPUT.formats`)
- **Dashboard**: `outputs/index.html` is a browsable catalog of every generated report, and `outputs/INDEX.md` keeps a Markdown index (`OUTPUT.update_dashboard`, `OUTPUT.update_index`)
- Automatic browse fallback through the free [Jina Reader](https://r.jina.ai) proxy when pages block plain scraping (`BROWSE.enable_jina_fallback`), plus a content-quality filter that rejects captcha walls, paywalls, and "access denied" pages
- Full CLI: override language, column/news counts, output formats, and output directory per run without editing `SETTINGS.yaml`
- RTL-aware HTML output and localized report labels for Chinese and Persian (English fallback for everything else)
- Keep prompt templates in [`./prompts`](./prompts) for easy editing
- Keep an independent [`./tools`](./tools) layer so search/browse can be replaced without touching the main workflow
- Keep flow construction in [`./workflow`](./workflow) so orchestration can evolve independently from collector logic

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

If you install Agently manually, make sure you use at least:

```bash
pip install "agently>=4.0.8.3"
```

2. Configure the model in [`SETTINGS.yaml`](./SETTINGS.yaml):

**Easiest**: use a model preset. Set `MODEL` to just:

```yaml
MODEL:
  preset: groq        # or: openai, openrouter, deepseek, together, ollama
```

and put the matching key in `.env` (e.g. `GROQ_API_KEY=...`). Add
`AGENTLY_NEWS_MODEL=<model-id>` to switch models without touching YAML.
`preset: ollama` needs no key and defaults to `qwen2.5:7b` locally.

**Advanced**: keep the model block explicit, with `${ENV.xxx}` placeholders
resolved from the environment or a local `.env` file:

```yaml
MODEL:
  provider: OpenAICompatible
  base_url: ${ENV.DEEPSEEK_BASE_URL}
  model: ${ENV.DEEPSEEK_DEFAULT_MODEL}
  model_type: chat
  auth:
    api_key: ${ENV.DEEPSEEK_API_KEY}
  request_options:
    temperature: 0.2
```

If your OpenAI-compatible endpoint does not require authentication, leave the
API key unset and the project will skip `auth`.

3. Run:

```bash
python app.py                # prompts for a topic interactively
python app.py "AI agents"    # or pass the topic directly
python app.py --ui           # or drive everything from the browser
```

## CLI reference

```bash
python app.py [topic ...] [options]
```

| Option | Meaning | Default |
|---|---|---|
| `topic` (positional) | Topic to collect news about (multiple words are joined). If omitted — and none of `--all` / `--dev` / `--weekly` / `--ui` / `--rerender` is given — you are prompted interactively. | — |
| `-s, --settings PATH` | Alternative settings file | `SETTINGS.yaml` |
| `-l, --language NAME` | Output language, any free-form name (English, Persian, Chinese, ...) | from settings |
| `-c, --max-columns N` | Max number of report columns | from settings |
| `-n, --max-news N` | Max stories per column | from settings |
| `-f, --formats ...` | Which files to save: `markdown json html` (markdown is always written) | from settings |
| `-o, --output-dir DIR` | Where to save reports | `outputs` |
| `-a, --all` | Generate a report for every topic under `TOPICS` | off |
| `--dev` | Developer Pulse mode (see below) | off |
| `--weekly` | Weekly digest of the last 7 days of reports | off |
| `--rerender` | Re-render all existing reports from their JSON with the current design (no LLM calls) | off |
| `--ui` | Open the local web control panel | off |
| `--port N` | Port for the web panel (probes up to 20 higher ports if busy) | `8899` |
| `--no-browser` | With `--ui`: start the panel without opening a browser tab (used by the Windows-autostart launcher) | off |
| `--bot` | Run the two-way Telegram bot: answers `/news <topic>`, `/dev` and `/weekly` sent from the configured `chat_id` and delivers the report back to that chat | off |
| `--allow-repeats` | Keep stories that appeared in previous reports (instead of skipping them) and badge the fresh ones `NEW` | off |
| `--no-tldr` | Skip the Key Takeaways summary | off |
| `--no-deliver` | Skip Telegram/webhook delivery for this run | off |
| `--quiet` | Print only saved file paths | off |
| `--debug` | Verbose logging | off |

Example:

```bash
python app.py "AI agents" --language Persian --max-columns 3 --max-news 3 \
  --formats markdown json html --quiet
```

## Configuration

### SETTINGS.yaml reference

All keys accept UPPERCASE or lowercase. `${VAR}` / `${ENV.VAR}` placeholders
are resolved from the environment and `.env`.

| Section | Keys | What it controls |
|---|---|---|
| `DEBUG` | bool | Verbose logging |
| `TOPICS` | list of strings | Topics used by `--all` |
| `PROXY` | url | Shared proxy for model / search / browse (each section can override) |
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

The settings loader also keeps basic compatibility with old v3 keys
(`MODEL_PROVIDER`, `MODEL_URL`, `MODEL_AUTH`, `MODEL_OPTIONS`,
`MAX_COLUMN_NUM`, `USE_CUSTOMIZE_OUTLINE`).

### Model presets

`MODEL.preset` expands to a full provider block — you only supply the API key:

| Preset | .env key | Default model |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| `openrouter` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `together` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| `ollama` | — (local, no key) | `qwen2.5:7b` @ `localhost:11434` |

Set `AGENTLY_NEWS_MODEL` in `.env` (or `model:` in YAML) to override the
preset's default model. Cloud presets fail fast with a clear error if the key
is missing; `ollama` never needs one.

### Environment variables (.env)

A local `.env` next to the project (or next to the exe) is loaded on start —
existing environment variables are never overridden.

| Variable | Used for |
|---|---|
| `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `TOGETHER_API_KEY` | Per-preset API keys |
| `AGENTLY_NEWS_MODEL` | Override the preset's default model id |
| `CUSTOM_API_KEY` | API key for the panel's "custom" provider option |
| `GITHUB_TOKEN` | Optional — raises GitHub API limits in dev mode from 60 to 5000 req/h |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram delivery |
| `NEWS_WEBHOOK_URL` | Webhook delivery |
| `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL`, `DEEPSEEK_API_KEY` | Referenced by the sample `SETTINGS.yaml` advanced model block |

### settings.overrides.json

The web panel never edits `SETTINGS.yaml`. Instead it writes a sidecar
`settings.overrides.json` next to it, which is overlaid onto the parsed YAML
before env resolution — so your YAML comments and formatting survive. When an
override sets `MODEL.preset`, the base `MODEL` block is replaced (keeping only
`request_options`) so stale `base_url`/`auth` placeholders can't shadow the
preset. Delete the file to fall back to pure `SETTINGS.yaml`.

## Web control panel

```bash
python app.py --ui            # opens http://127.0.0.1:8899/
python app.py --ui --port 9000
```

Double-clicking `DailyNewsCollector.exe` (no arguments) opens the panel
automatically. The panel has exactly two pages:

**The desk** (home) —

- start a run (topic, language, column/news counts, allow-repeats) with one line,
  or launch **Developer Pulse** / **Weekly digest** from the quick links
- reuse configured `TOPICS` as quick-fill links; press `/` to focus the input
- while a run is in progress the **pipeline stage line** (سرفصل ← جست‌وجو ←
  گزینش ← خلاصه ← نگارش ← خروجی) lights up stage by stage, inferred from the
  live log, with a thin progress rule underneath; in Developer Pulse runs a
  row of **source-health chips** shows how many items each channel returned
  (or that it failed)
- the **wire line** always shows the latest log line; click it to expand a
  compact terminal (auto-expands during a run)
- a **stats strip** above the archive: total reports, last-7-days count, and
  the current daily streak
- the archive is a date-grouped, searchable newspaper index with kind filters
  (news / dev / weekly); hovering a row reveals raw HTML/MD/JSON links
- the ⚙ button opens the **settings modal** — model (provider, model id, API
  key, live connection test), report (language, tone, column/news counts,
  quick-topic list), Developer Pulse sources (subreddits, watched repos, extra
  RSS feeds, GitHub language), Telegram (bot token, channel, optional
  telegram-only proxy, live test-send), the daily **scheduler**
  (dev/topic/weekly at HH:MM while the panel is open), and a **start with
  Windows** toggle that drops a silent `--ui --no-browser` launcher into the
  Startup folder

**The paper** (reader) — click any archive row to read the report inside the
panel: key takeaways, a column table-of-contents, numbered sections, full
story summaries with REPO/RELEASE/SECURITY/LAUNCH tags, "why it was picked"
margin notes, source links with one-click copy, a reading-progress bar,
font-size controls, print/PDF styling, estimated reading time, and a
**send-to-Telegram** button for any archived report. `Esc` returns to the
desk. The panel also ships a web-app manifest + icon, so you can install it
as a standalone window from the browser menu.

An **ink/paper** (dark/light) theme toggle is in the header, persisted per
browser.

The panel binds to `127.0.0.1` only — it is not reachable from the network.
The server serves [`./webui`](./webui) (or the copy bundled inside the exe) and
falls back to a built-in inline HTML page if the folder is missing, so the
panel always works.

For scripting, the panel exposes a small local API:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/state` | GET | Running flag, current topic, last report, model label, recent log lines |
| `/api/run` | POST | Start a run (`topic`, `dev`, `weekly`, `language`, `max_columns`, `max_news`, `allow_repeats`); `409` if already running |
| `/api/reports` | GET | Catalog of all generated reports |
| `/reports/<name>` | GET | Serve one report file (path-guarded to the output dir) |
| `/api/settings` | GET / POST | Read or save model/workflow settings (writes `settings.overrides.json` + `.env` key) |
| `/api/settings/test` | POST | Live connectivity check against the provider |

## Developer Pulse mode

```bash
python app.py --dev --quiet          # or click "نبض برنامه‌نویسی" in the panel
DailyNewsCollector.exe --dev
```

Five fixed columns, no web search and no LLM outline step:

| Column | Sources |
|---|---|
| Trending Repositories | `github.com/trending` (daily) + GitHub Rising (repos gaining stars unusually fast in ~24-48h via OSS Insight, even if never on the trending page; falls back to weekly trending) + GitHub search for repos created in the last week with fast-growing stars |
| Fresh Releases | New releases of your `watch_repos` — changelog summarized as "what changed / anything breaking / upgrade or wait" |
| Security Watch | Fresh high-severity GitHub Security Advisories for your `security_ecosystems` (pip, npm, ...) — affected versions, impact, concrete fix |
| Hot Developer News | Hacker News (Algolia API, falls back to hnrss.org when Algolia is unreachable) |
| Product Radar | Developer-relevant launches from today's Product Hunt front page |
| Community Buzz | Reddit top-of-day from configured subreddits + Lobsters hottest + dev.to top articles + daily.dev most-upvoted + custom `extra_feeds` |

The Fresh Releases and Security Watch columns disappear automatically when
`watch_repos` / `security_ecosystems` are set to empty lists. Set your
`stack` (e.g. Python, React) and summaries add a sentence on what each item
means for *your* stack when genuinely relevant. Releases, advisories, and
Reddit self posts ship their content inline — no extra page fetches. All
channels are fetched in parallel, failures are skipped silently (the remaining
channels fill the columns), and an optional `GITHUB_TOKEN` in `.env` raises
GitHub API rate limits from 60 to 5000 requests/hour.

For GitHub repository links, the summarizer fetches the README plus repo
metadata (stars, language, license, dates) instead of scraping HTML, and a
dedicated prompt introduces the repo like a colleague would: what it does,
how it works, where you'd actually use it, and why it's blowing up.

**Trend streaks**: a persistent memory (`outputs/.trends.json`) tracks how many
consecutive days each repo has appeared on trending. Repos with a streak of 2+
get a "🔥 trending N days in a row" flag in their summary context; entries not
seen for 14 days are pruned.

All knobs live in `SETTINGS.yaml` under `DEV_PULSE`:

| Key | Default | Meaning |
|---|---|---|
| `reddit_subreddits` | `programming, webdev, LocalLLaMA` | Subreddits for Community Buzz |
| `min_hn_points` | `80` | Minimum Hacker News points |
| `min_reddit_score` | `150` | Minimum Reddit score |
| `min_lobsters_score` | `10` | Minimum Lobsters score |
| `min_devto_reactions` | `20` | Minimum dev.to reactions |
| `min_dailydev_upvotes` | `20` | Minimum daily.dev upvotes |
| `extra_feeds` | `[]` | Custom RSS/Atom feeds merged into Community Buzz (X via RSSHub, blogs, …) |
| `github_language` | — | Optional language filter for trending/new repos |
| `watch_repos` | `ollama/ollama, microsoft/vscode, python/cpython, nodejs/node` | Repos for Fresh Releases (empty list disables the column) |
| `release_window_days` | `3` | How far back to look for releases |
| `security_ecosystems` | `pip, npm` | Ecosystems for Security Watch (empty list disables the column) |
| `security_min_severity` | `high` | Minimum advisory severity (`low`/`medium`/`high`/`critical`) |
| `stack` | `[]` | Your stack — adds a "what this means for you" sentence when relevant |

X/Twitter is intentionally not included: it has no free API and scraping it is
unreliable; HN and Reddit carry the same stories.

## Weekly digest

```bash
python app.py --weekly               # or click "جمع‌بندی هفتگی" in the panel
```

Reads the stored **JSON** of every report from the last 7 days, feeds a compact
view of all their stories to a "chief editor" prompt
([`prompts/write_weekly.yaml`](./prompts/write_weekly.yaml)), and produces one
"Highlights of the Week" report: a 2–3 paragraph narrative overview plus 5–8
selected highlights, each linked back to its original story. The digest is
written through the same output pipeline (Markdown / JSON / HTML, index,
dashboard, delivery). If there are no reports in the window, it says so and
exits cleanly.

## RSS feed sources

Search engines occasionally rate-limit or return nothing. Add RSS/Atom feeds
as a reliable extra candidate pool — items are keyword-matched per column and
merged with search results before shortlisting:

```yaml
SEARCH:
  rss_feeds:
    - https://techcrunch.com/category/artificial-intelligence/feed/
    - https://www.theverge.com/rss/index.xml
```

## Multiple topics in one run

```yaml
TOPICS:
  - AI agents
  - large language models
```

```bash
python app.py --all --quiet
```

Each topic produces its own report (and its own Telegram delivery if enabled).

## Delivery: Telegram & webhook

### Telegram

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Find your chat id (e.g. message [@userinfobot](https://t.me/userinfobot)).
3. Add to `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
```

4. Set `DELIVERY.telegram.enabled: true` in `SETTINGS.yaml`. Each run then sends a
   compact digest message plus the standalone HTML report as an attachment
   (`send_html_file: false` to skip the attachment).

### Webhook

Set `NEWS_WEBHOOK_URL` in `.env` and `DELIVERY.webhook.enabled: true` — each
finished report is POSTed as JSON (title, takeaways, columns, markdown) to that
URL, ready for Slack/Discord bridges, n8n/Zapier flows, or your own service.

Delivery failures are logged but never abort a run — your report is always
saved locally first.

## Outputs, dashboard, history

Every run writes to `OUTPUT.directory` (default `./outputs`):

- `<title>_<date>.md` — the Markdown report (always written)
- `<title>_<date>.json` — full structured data, used by `--rerender` and `--weekly`
- `<title>_<date>.html` — standalone styled page, no external dependencies required
- `INDEX.md` — Markdown index of all reports (`OUTPUT.update_index`)
- `index.html` + `reports.json` — browsable dashboard/catalog of all reports (`OUTPUT.update_dashboard`)
- `.history.json` — published-story memory for freshness (`HISTORY`, 30-day retention by default)
- `.trends.json` — trend-streak memory for Developer Pulse

Because every report keeps its JSON, `python app.py --rerender` can rebuild all
HTML/Markdown files with the current design at any time — instantly and
without any LLM calls.

## Report design

The standalone HTML report ([`news_collector/html_report.py`](./news_collector/html_report.py)) ships with:

- editorial layout with sticky column navigation and scrollspy highlighting
- per-story kind badges (REPO / RELEASE / SECURITY), numbered Key Takeaways,
  and "Why it matters" callouts
- automatic dark/light mode via `prefers-color-scheme`, print styles, and
  entrance motion that respects `prefers-reduced-motion`
- full RTL support: Persian/Arabic/Hebrew/Urdu reports render `dir="rtl"`, and
  mixed RTL/LTR story titles stay correct via `dir=auto` + `unicode-bidi: plaintext`
- Vazirmatn + JetBrains Mono typography loaded as progressive enhancement with
  system-font fallbacks (reports stay readable fully offline)

Report labels are localized for Chinese and Persian, with English fallback for
every other language.

## Frontend development (zero-build)

The whole panel is one hand-written file: [`webui/index.html`](./webui/index.html)
(vanilla HTML/CSS/JS, Persian/RTL-first, self-contained — no npm, no bundler,
no build step). To hack on it:

```bash
python app.py --ui       # serve the panel
# edit webui/index.html, refresh the browser — that's it
```

The Python server serves `./webui` when it exists (or the copy bundled inside
the exe) and falls back to the built-in legacy page in
`news_collector/webui_html.py` otherwise. The page polls `/api/state` for live
status and uses hash routing (`#r=<report>.json`) for the reader page.

## Build a standalone Windows executable

Preferred — build from the shipped spec (it already includes the hook fix and
bundles `SETTINGS.yaml`, `prompts/`, and `webui/`):

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

> `--additional-hooks-dir packaging/hooks` is required: it overrides a
> pyinstaller-hooks-contrib hook for an unrelated PyPI package called
> `workflow` that collides with this project's local `workflow` package.

The result is `dist/DailyNewsCollector.exe`. On first run it extracts a default
`SETTINGS.yaml` and `prompts/` next to itself so you can edit them; `outputs/`,
`logs/`, and history live next to the exe as well. Put a `.env` file next to
the exe for model / Telegram credentials, then:

```powershell
DailyNewsCollector.exe                # double-click = opens the web panel
DailyNewsCollector.exe "AI agents" --quiet
DailyNewsCollector.exe --all          # every topic in TOPICS
DailyNewsCollector.exe --dev          # Developer Pulse
```

## Docker

A minimal [`Dockerfile`](./Dockerfile) is included (Python 3.10 base,
`pip install -r requirements.txt`, `CMD python app.py`):

```bash
docker build -t agently-news .
docker run --rm -it --env-file .env \
  -v "$PWD/outputs:/app/outputs" agently-news \
  python app.py "AI agents" --quiet
```

Mount `outputs/` to keep reports and history on the host. The image runs the
CLI; it does not expose the panel port by default.

## Run it every day automatically

Windows (Task Scheduler):

```powershell
schtasks /Create /TN "DailyNewsCollector" /SC DAILY /ST 08:00 `
  /TR "cmd /c cd /d D:\Agently-Daily-News-Collector-main && python app.py \"AI agents\" --quiet"
```

Linux/macOS (cron):

```bash
0 8 * * * cd /path/to/Agently-Daily-News-Collector && python app.py "AI agents" --quiet
```

Combined with `HISTORY` (no repeated stories) and `DELIVERY` (Telegram push),
this turns the project into a fully automatic daily briefing service. Add a
weekly cron line with `--weekly` for the Friday roundup.

## Project structure

```text
.
├── app.py                     # thin entry point -> news_collector.cli.main
├── SETTINGS.yaml              # all configuration (model, search, workflow, delivery, ...)
├── requirements.txt           # agently>=4.0.8.3, PyYAML, ddgs, beautifulsoup4, python-dotenv, httpx
├── Dockerfile
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

## Important v3 -> v4 Changes

The business chain is still roughly:

`outline -> search -> pick -> browse + summarize -> write column -> render markdown`

What changed is the engineering shape around that chain.

### Project-level changes

- The old v3 project used a main workflow plus a nested column workflow under `./workflows`, with custom `search.py` / `browse.py` helpers and storage-style state passing.
- The v4 project separates responsibilities more clearly:
  - `news_collector/`: app/integration layer
  - `workflow/`: parent flow, column sub flow, and concrete chunk logic
  - `tools/`: search/browse adapter layer
  - `prompts/`: structured prompt contracts
- Model configuration is no longer hardcoded in Python. It now uses `${ENV.xxx}` placeholders from `SETTINGS.yaml`, so deployment and local switching are simpler.
- Tool wiring is no longer buried inside workflow code. Search, browse, and logger are injected as TriggerFlow runtime resources, which makes the workflow easier to replace or test.
- The workflow plan is now closer to the business boundary:
  - parent flow: `prepare_request -> generate_outline -> for_each(column) -> render_report`
  - column sub flow: `search -> pick -> summarize -> write_column`
  - the `summarize` stage inside the column flow is further pushed down into a summary sub flow, where TriggerFlow handles fan-out and collection directly instead of leaving `asyncio.gather` in business code
  - this keeps the parent focused on report orchestration and the child focused on one column lifecycle
  - the immediate value of `sub flow` here is that the column pipeline becomes a reusable, independently evolvable workflow unit instead of staying buried inside one oversized parent chunk

### Agently v4 features used here

- **TriggerFlow orchestration**
  - Replaces the old v3 workflow style with a more explicit flow graph (`to`, `for_each`, `sub flow`, branching-ready composition).
  - Unlike the old v3 Workflow chain, TriggerFlow here runs columns concurrently and also summarizes picked stories concurrently within each column.
  - Meaning for this project: the end-to-end news pipeline is easier to inspect, evolve, and split into chunks without mixing orchestration with business logic, while the parent report flow and the per-column pipeline can now be modeled directly as parent/child flows instead of one oversized chunk.
- **Sub flow composition**
  - The project can now extract a naturally repeated business pipeline, “build one column”, into its own TriggerFlow and invoke it repeatedly from the parent flow inside `for_each(column)`.
  - Meaning for this project:
    - the parent flow stays focused on report-level orchestration
    - the column pipeline can be tested, visualized, and exported independently
    - future variants such as “briefing column”, “deep-dive column”, or “regional column” can reuse or derive from the child flow instead of cloning parent-flow nodes
    - `capture / write_back` makes the boundary between parent and child explicit for input, state, and resources
- **Structured output contracts**
  - YAML prompts now define output schema directly for outline generation, news picking, summarizing, and column writing.
  - Meaning for this project: much less handwritten parsing glue, clearer interfaces between steps, and easier prompt iteration.
- **Built-in Search / Browse tools**
  - The project now defaults to Agently v4 built-in tool implementations instead of the old project-local helpers.
  - Meaning for this project: less custom infrastructure code, and users can still swap implementations through `./tools` without rewriting the workflow.
- **Runtime resources and state namespaces**
  - TriggerFlow runtime resources are used to inject logger/search/browse dependencies, while runtime state stores execution data such as request, outline, and intermediate results.
  - Meaning for this project: dependency wiring and execution state are separated cleanly, which keeps chunk code thinner and more maintainable.
- **Environment-aware settings**
  - Agently v4 `set_settings(..., auto_load_env=True)` works directly with `${ENV.xxx}` placeholders.
  - Meaning for this project: model endpoint, model name, and API key can be switched by environment instead of editing code or committing secrets.

### Overall effect on this project

- The core product behavior remains familiar to v3 users, but the project now has a cleaner app/workflow/tools/prompts split.
- More logic is expressed in Agently-native capabilities instead of project-specific glue code.
- True concurrency is now part of the default execution model. The v3 version was effectively serial, while the v4 version can process columns and per-column summaries in parallel through TriggerFlow.
- Replacing tools, adjusting prompts, or evolving workflow steps is now lower-risk than in the old v3 layout, and the overall orchestration shape is again aligned with the original “main flow + column flow” mental model.
- It also means workflow evolution can happen by layer: report-level changes stay in the parent flow, while column-level changes stay in the sub flow instead of forcing both to change together.

## Notes

- Python `>=3.10` is required because Agently v4 requires it.
- This project requires Agently `>=4.0.8.3`.
- Model settings use `${ENV.xxx}` placeholders resolved from the environment / `.env` (Agently v4 `auto_load_env=True`), or the simpler `MODEL.preset` shortcut.
- `tools/` defaults to Agently v4 built-in implementations, but you can replace the factories there with your own tools (see [`tools/README.md`](./tools/README.md)).
- `workflow/` is split by business boundary into the parent flow, the column sub flow, report-level chunks, and column-level chunks.
- `news_collector/` acts as the app/integration layer for configuration, model wiring, CLI, web panel, rendering, and delivery.
- The sample [`SETTINGS.yaml`](./SETTINGS.yaml) ships with `BROWSE.enable_playwright: false` and `enable_jina_fallback: true`; enable Playwright for better browse quality on dynamic or protected news sites (`pip install playwright && playwright install chromium`).
- The interactive CLI prompt is bilingual (English/Chinese); the web panel UI is Persian/RTL-first; reports themselves follow `WORKFLOW.output_language`.
- A Chinese README for the original project is available at [`README_CN.md`](./README_CN.md) (may lag behind this file).
