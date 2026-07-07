# Daily News Collector

AI-powered daily news briefings on any topic, in any language — with a local
web control panel, a developer-focused pulse mode, weekly digests, Telegram
delivery, an RSS feed, and hands-free daily publishing to GitHub Pages.

Built on [Agently](https://github.com/AgentEra/Agently) v4 (TriggerFlow
workflows). Forked from
[AgentEra/Agently-Daily-News-Collector](https://github.com/AgentEra/Agently-Daily-News-Collector)
and heavily extended.

## Download (Windows)

Grab the standalone exe from
[**Releases**](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases)
— no Python needed. Unzip, create a `.env` with your LLM API key next to the
exe, then double-click (opens the web panel) or use the CLI.

## Quick start (from source)

```bash
pip install -r requirements.txt
echo DEEPSEEK_API_KEY=your_key_here > .env

python app.py --ui              # web control panel in your browser
python app.py "AI Agents"       # or straight from the terminal
python app.py --dev             # developer pulse: repos, releases, advisories, HN
python app.py --weekly          # digest of the last 7 days
python app.py --bot             # two-way Telegram bot: /news, /dev, /weekly
```

Reports land in `outputs/` as Markdown / HTML / JSON, with a browsable
dashboard (`outputs/index.html`) and an RSS feed (`outputs/feed.xml`).

## Highlights

- 🖥️ **Web control panel** (`--ui`) — run topics, schedule daily runs, browse
  the archive, edit settings; zero-build frontend in `webui/`.
- 🧑‍💻 **Developer pulse** (`--dev`) — GitHub trending/releases/advisories,
  Hacker News, Reddit, Lobsters, dev.to, with a TLDR digest.
- 📅 **Weekly digest** (`--weekly`) and design-only re-render (`--rerender`).
- 🤖 **Telegram bot** (`--bot`) — message `/news <topic>` to your bot and the
  briefing comes back to the same chat (whitelisted to your chat id).
- 📡 **RSS feed** — `outputs/feed.xml` regenerates with every report.
- 🔁 **Model fallback** — `MODEL.fallback_presets` retries the run on another
  provider (groq, openrouter, …) when the primary model fails.
- 🕵️ **Anti-repeat history** — stories already published are skipped
  (or kept and badged `NEW`-vs-repeat with `--allow-repeats`).
- 📬 **Delivery** — Telegram channel-style posts or webhook JSON.
- ⚙️ Everything configurable in [SETTINGS.yaml](SETTINGS.yaml); model presets
  for OpenAI, OpenRouter, Groq, DeepSeek, Together and local Ollama.

## Automated daily publishing

[.github/workflows/daily.yml](.github/workflows/daily.yml) runs the developer
pulse every morning and publishes `outputs/` to **GitHub Pages** — dashboard,
reports and RSS feed included. To enable it on your fork:

1. Repo **Settings → Pages** → Source: **GitHub Actions**.
2. Repo **Settings → Secrets and variables → Actions** → add
   `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL`
   (or edit `SETTINGS.yaml` to use a one-key `preset:` instead).
3. Wait for the schedule or run the workflow manually from the Actions tab.

Tagging a release (`git tag v1.1.0 && git push --tags`) triggers
[release.yml](.github/workflows/release.yml), which builds the Windows exe
and attaches it to the GitHub release automatically.

## Documentation

The full guide — CLI reference, every SETTINGS key, web panel, Docker,
PyInstaller packaging, architecture notes — lives in
[**docs/GUIDE.md**](docs/GUIDE.md).

## License

[Apache 2.0](LICENSE)
