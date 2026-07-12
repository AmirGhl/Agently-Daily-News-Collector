# Agently Daily News Collector

> **خلاصه‌های خبری روزانه با هوش مصنوعی روی هر موضوعی، به هر زبانی — با پنل کنترل وب لوکال، حالت نبض برنامه‌نویس، خلاصه هفتگی، تحویل تلگرام، فید RSS، و انتشار خودکار روزانه روی GitHub Pages.**

ساخته شده بر پایه **[Agently](https://github.com/AgentEra/Agently) نسخه ۴** (سیرکار TriggerFlow). فورک شده از [AgentEra/Agently-Daily-News-Collector](https://github.com/AgentEra/Agently-Daily-News-Collector) و به‌شکل قابل‌توجهی توسعه یافته.

[English README](README.md) · [راهنمای کامل](docs/GUIDE.md) · [ریلیزها](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases)

---

## فهرست مطالب

- [نکات برجسته](#نکات-برجسته)
- [شروع سریع](#شروع-سریع)
- [مرجع CLI](#مرجع-cli)
- [حالت‌ها و گردش‌کارها](#حالت‌ها-و-گردش‌کارها)
- [پنل کنترل وب](#پنل-کنترل-وب)
- [پیکربندی](#پیکربندی)
- [پیش‌تنظیم‌های مدل](#پیش‌تنظیم‌های-مدل)
- [تحویل: تلگرام و وب‌هوک](#تحویل-تلگرام-و-وب‌هوک)
- [خروجی‌ها و داشبورد](#خروجی‌ها-و-داشبورد)
- [انتشار خودکار روزانه](#انتشار-خودکار-روزانه)
- [ساخت فایل اجرای مستقل ویندوز](#ساخت-فایل-اجرای-مستقل-ویندوز)
- [داکر](#داکر)
- [ساختار پروژه](#ساختار-پروژه)
- [معماری](#معماری)
- [تغییرات مهم v3 → v4](#تغییرات-مهم-v3--v4)
- [مجوز](#مجوز)

---

## نکات برجسته

| ویژگی | توضیح |
|---------|-------------|
| 🖥️ **پنل کنترل وب** (`--ui`) | اجرای موضوعات، برنامه‌ریزی اجراهای روزانه، مرور آرشیو، ویرایش تنظیمات — فرانت‌اند zero-build در `webui/` |
| 🧑‍💻 **نبض برنامه‌نویس** (`--dev`) | GitHub Trending/Releases/Advisories، Hacker News، Reddit، Lobsters، dev.to، daily.dev، Product Hunt — با نشان‌های سرعت (velocity) و استریک روند (trend streaks) |
| 📅 **خلاصه هفتگی** (`--weekly`) | ترکیب ۷ روز اخیر گزارش‌ها در یک مرور روایی |
| 🤖 **ربات تلگرام** (`--bot`) | ربات دوطرفه: `/news <موضوع>`، `/dev`، `/weekly` بفرستید و خلاصه در همین چت برگردد |
| 📡 **فید RSS** | `outputs/feed.xml` با هر گزارش بازسازی می‌شود |
| 🔁 **فول‌بک مدل** | `MODEL.fallback_presets` در صورت خطای مدل اصلی، اجرا را روی ارائه‌دهنده دیگر (groq، openrouter، …) مجدد می‌کند |
| 🕵️ **تاریخچه ضدتکرار** | خبرهای قبلاً منتشرشده رد می‌شوند (یا با `--allow-repeats` نگه‌داشته شده و برچسب `NEW` می‌گیرند) |
| 📬 **تحویل** | پست‌های کانال‌مانند تلگرام یا JSON وب‌هوک |
| ⚙️ **پیکربندی کامل** | همه‌چیز در [`SETTINGS.yaml`](SETTINGS.yaml)؛ پیش‌تنظیم مدل برای OpenAI، OpenRouter، Groq، DeepSeek، Together، Ollama |
| 🎨 **گزارش‌های بازطراحی‌شده** | چیدمان ویرایشی، ناوبری اسکرول‌اسپای چسبان، برچسب نوع (REPO/RELEASE/SECURITY)، پشتیبانی RTL، حالت تیره/روشن، استایل چاپ، انیمیشنagger (آگاه از prefers-reduced-motion) |
| ♻️ **`--rerender`** | بازرندر همه گزارش‌های موجود از JSON با طراحی کنونی — بدون فراخوانی LLM |

---

## شروع سریع

### از سورس (پایتون)

```bash
# 1. کلون و نصب
git clone https://github.com/AmirGhl/Agently-Daily-News-Collector.git
cd Agently-Daily-News-Collector
pip install -r requirements.txt

# 2. کلید API مدل را اضافه کنید
echo DEEPSEEK_API_KEY=your_key_here > .env

# 3. اجرا کنید
python app.py "AI agents"           # یک‌باره از ترمینال
python app.py --ui                  # پنل کنترل وب
python app.py --dev                 # نبض برنامه‌نویس
python app.py --weekly              # خلاصه هفتگی
python app.py --bot                 # ربات تلگرام دوطرفه
```

### فایل اجرای مستقل ویندوز (بدون نیاز به پایتون)

`DailyNewsCollector.exe` را از [**Releases**](https://github.com/AmirGhl/Agently-Daily-News-Collector/releases) دانلود کنید → از حالت فشرده خارج کنید → یک فایل `.env` با کلید API کنار exe بسازید → دو بار کلیک کنید (پنل وب باز می‌شود) یا از CLI اجرا کنید:

```powershell
DailyNewsCollector.exe "AI agents" --quiet
DailyNewsCollector.exe --dev
DailyNewsCollector.exe --all
```

---

## مرجع CLI

```bash
python app.py [topic ...] [options]
```

| گزینه | معنی | پیش‌فرض |
|--------|------|---------|
| `topic` (positional) | موضوع جمع‌آوری خبر (کلمات با هم ادغام می‌شوند). اگر حذف شود و هیچ فلگی داده نشود، به‌شکل تعاملی پرسیده می‌شود. | — |
| `-s, --settings PATH` | فایل تنظیمات جایگزین | `SETTINGS.yaml` |
| `-l, --language NAME` | زبان خروجی (هر نام آزاد: English، Persian، Chinese، ...) | از تنظیمات |
| `-c, --max-columns N` | حداکثر تعداد ستون‌های گزارش | از تنظیمات |
| `-n, --max-news N` | حداکثر خبر در هر ستون | از تنظیمات |
| `-f, --formats ...` | کدام فایل‌ها ذخیره شوند: `markdown json html` (markdown همیشه نوشته می‌شود) | از تنظیمات |
| `-o, --output-dir DIR` | دایرکتوری ذخیره گزارش‌ها | `outputs` |
| `-a, --all` | گزارش برای هر موضوع در `TOPICS` بساز | off |
| `--topics "a,b,c"` | موضوعات جدا شده با کاما را به‌صورت موازی اجرا و در یک گزارش ادغام کن | off |
| `--dev` | حالت نبض برنامه‌نویس (GitHub، HN، Reddit، …) | off |
| `--weekly` | خلاصه هفتگی ۷ روز اخیر | off |
| `--rerender` | همه گزارش‌ها را از JSON با طراحی کنونی بازرندر کن (بدون LLM) | off |
| `--ui` | پنل کنترل وب محلی را باز کن | off |
| `--port N` | پورت پنل وب (تا ۲۰ پورت بالاتر проб می‌کند) | `8899` |
| `--no-browser` | با `--ui`: پنل را بدون باز کردن تب مرورگر راه‌اندازی کن (برای autostart) | off |
| `--bot` | ربات تلگرام دوطرفه اجرا کن: به `/news`، `/dev`، `/weekly` پاسخ می‌دهد | off |
| `--allow-repeats` | خبرهای تکراری را نگه‌دار (خبرهای تازه برچسب `NEW` می‌گیرند) | off |
| `--no-tldr` | خلاصه نکات کلیدی را رد کن | off |
| `--no-deliver` | تحویل تلگرام/وب‌هوک را برای این اجرا غیرفعال کن | off |
| `--quiet` | فقط مسیر فایل‌های ذخیره‌شده را چاپ کن | off |
| `--debug` | لاگ کردن مفصل | off |

**مثال‌ها**

```bash
# ادغام چند موضوع
python app.py --topics "AI agents,LLMs,AI coding" --formats markdown json html

# گزارش فارسی، ۳ ستون، ۳ خبر در ستون، حالت 조용
python app.py "AI agents" --language Persian --max-columns 3 --max-news 3 --quiet

# همه موضوعات پیکربندی‌شده یک‌جا
python app.py --all --quiet
```

---

## حالت‌ها و گردش‌کارها

### حالت موضوع استاندارد (پیش‌فرض)

```
سرفصل → جست‌وجو → گزینش → مرور + خلاصه‌سازی → نگارش ستون → رندر گزارش
```

- یک LLM «رئیس‌ویراستار» طرح گزارش را طراحی می‌کند: عناوین ستون، الزامات، و کلمات‌کلیدی جست‌وجو (یا شما یک سرفصل ثابت از طریق `OUTLINE.use_customized` بدهید).
- هر ستون جست‌وجو می‌کند (وب + RSS اختیاری)، یک LLM کاندیداها را میان‌بر می‌کند، صفحات برگزیده مرور می‌شوند (Playwright / فول‌بک Jina Reader) و به‌صورت **موازی** خلاصه می‌شوند.
- ستون‌ها به‌صورت موازی نگارش می‌شوند، گزارش نکات کلیدی (TL;DR) از LLM می‌گیرد، موارد تکراری بین ستون‌ها حذف می‌شوند، و همه‌چیز به Markdown / JSON / HTML رندر می‌شود.

### نبض برنامه‌نویس (`--dev`)

شش ستون ثابت، **بدون جست‌وجوی وب، بدون گام سرفصل از LLM**:

| ستون | منابع |
|--------|---------|
| **مخازن ترندینگ** | GitHub Trending روزانه + GitHub Rising (مخازنی که به‌صورت غیرعادی سریع ستاره می‌گیرند در ~۲۴–۴۸ ساعت از طریق OSS Insight) + جست‌وجوی GitHub برای مخازن ساخته‌شده هفته گذشته با رشد ستاره سریع |
| **انتشارات تازه** | ریلیزهای جدید `watch_repos` شما — چن‌لاگ به‌شکل «چه‌چیزی تغییر کرد / چیزی خراب شده / آپگرید کن یا صبر کن» خلاصه می‌شود |
| **نگهبان امنیت** | هشدارهای امنیتی GitHub با شدت بالا برای `security_ecosystems` شما (pip، npm، go، rust، maven، nuget، rubygems، composer، pub) — نسخه‌های تحت‌تأثیر، اثر، و رفع قطع |
| **اخبار داغ برنامه‌نویس** | Hacker News (API Algolia، فول‌بک hnrss.org) |
| **رادار محصول** | راه‌اندازی‌های مرتبط با برنامه‌نویس از صفحهٔ امروز Product Hunt |
| **سوگند جامعه** | Reddit برترین‌های روز از ساب‌ردیت‌های پیکربندی‌شده + Lobsters داغ‌ترین‌ها + dev.to مقالات برتر + daily.dev بیشترین‌اپ‌ووت + `extra_feeds` سفارشی |

- **استریک روند (Trend streaks)**: مخازنی که چند روز متوالی ترندینگ باشند، پرچم‌گذاری می‌شوند (🔥 trending N days) از طریق حافظه ماندگار (`outputs/.trends.json`).
- **استک شما**: `DEV_PULSE.stack` را ست کنید (مثلا `Python`، `React`) و خلاصه‌ها زمانی که واقعاً مرتبط باشند جمله «چه معنایی برای شما دارد» اضافه می‌کنند.
- همه کانال‌ها به‌صورت موازی واکشی می‌شوند؛ خطاها به‌صورت خاموش نادیده گرفته می‌شوند. `GITHUB_TOKEN` اختیاری در `.env` محدودیت نرخ API گیت‌هاب را از ۶۰ به ۵۰۰۰ درخواست در ساعت بالا می‌برد.
- برای لینک‌های مخزن گیت‌هاب، خلاصه‌ساز README و متادیتای مخزن (ستاره، زبان، لایسنس، تاریخ‌ها) را واکشی می‌کند به‌جای اسکراپ HTML، و یک پرامپت مخصوص مخزن را مثل همکار معرفی می‌کند: چی کار می‌کند، چطور کار می‌کند، کجا استفاده می‌شود، و چرا در حال ترند شدن است.

### خلاصه هفتگی (`--weekly`)

JSON ذخیره‌شده هر گزارش از ۷ روز اخیر خوانده می‌شود، نمای فشرده همه داستان‌ها به یک پرامپت «رئیس‌ویراستار» ([`prompts/write_weekly.yaml`](prompts/write_weekly.yaml)) داده می‌شود، و یک گزارش «نکات برجسته هفته» تولید می‌کند: یک مرور روایی ۲–۳ پاراگرافی به‌علاوه ۵–۸ هایلایت منتخب، هر کدام لینک‌دار به داستان اصلی. از همان پایپ‌لاین خروجی نوشته می‌شود (Markdown / JSON / HTML، ایندکس، داشبورد، تحویل). اگر گزارشی در پنجره وجود نداشته باشد، به‌شکل تمیز خارج می‌شود.

### ربات تلگرام دوطرفه (`--bot`)

`python app.py --bot` اجرا کنید (یا در پنل وب فعال کنید). ربات به پیام‌ها از `chat_id` پیکربندی‌شده گوش می‌دهد:

- `/news <موضوع>` — خلاصه استاندارد بساز
- `/dev` — نبض برنامه‌نویس بساز
- `/weekly` — خلاصه هفتگی بساز

گزارش‌ها به همان چت بازگردانده می‌شوند.

---

## پنل کنترل وب

```bash
python app.py --ui            # باز می‌کند http://127.0.0.1:8899/
python app.py --ui --port 9000
```

**دو بار کلیک روی `DailyNewsCollector.exe` (بدون آرگومان) به‌صورت خودکار پنل را باز می‌کند.**

پنل دقیقاً دو صفحه دارد:

### میز (Desk) — صفحه اصلی

- اجرای یک ران (موضوع، زبان، تعداد ستون/خبر، allow-repeats) با یک خط، یا راه‌اندازی **نبض برنامه‌نویس** / **خلاصه هفتگی** از لینک‌های سریع
- استفاده مجدد از `TOPICS` پیکربندی شده به‌عنوان لینک‌های پرکردن سریع؛ `/` بزنید تا روی ورودی فوکوس شود
- **خط مراحل پایپ‌لاین** (سرفصل ← جست‌وجو ← گزینش ← خلاصه ← نگارش ← خروجی) مرحله‌به‌مرحله روشن می‌شود، استنباط شده از لاگ زنده، با یک نوار پیشرفت نازک زیرش؛ در ران‌های نبض برنامه‌نویس یک ردیف **چیپ‌های سلامت منبع** تعداد آیتم‌های هر کانال را نشان می‌دهد (یا اینکه شکست خورده)
- **خط سیم (Wire line)** همیشه آخرین خط لاگ را نشان می‌دهد؛ کلیک کنید تا ترمینال فشرده باز شود (در حین ران به‌صورت خودکار باز می‌شود)
- **نوار آمار**: کل گزارش‌ها، تعداد ۷ روز اخیر، استریک روزانه جاری
- **آرشیو**: شاخص روزنامه‌ای گروه‌بندی شده بر اساس تاریخ، قابل جست‌وجو، با فیلتر نوع (news / dev / weekly); هاور روی ردیف برای لینک‌های خام HTML/MD/JSON
- **دکمه ⚙ تنظیمات** — مدل (ارائه‌دهنده، شناسه مدل، کلید API، تست اتصال زنده)، گزارش (زبان، لحن، تعداد ستون/خبر، لیست موضوعات سریع)، منابع نبض برنامه‌نویس (ساب‌ردیت‌ها، مخازن تحت‌مراقبه، فیدهای RSS اضافه، زبان گیت‌هاب)، تلگرام (توکن ربات، کانال، پراکسی اختیاری فقط‌تلگرام، تست‌ارسال زنده)، **برنامه‌ریز روزانه** (dev/topic/weekly در HH:MM selama پنل باز است)، و توگل **شروع با ویندوز** (لانچر `--ui --no-browser` بی‌صدا در پوشه Startup می‌ریزد)

### کاغذ (Paper) — خواندن گزارش

هر ردیف آرشیو را کلیک کنید تا گزارش در پنل بخوانید:

- نکات کلیدی، mục lục ستون‌ها، بخش‌های شماره‌دار، خلاصه کامل داستان‌ها با برچسب REPO/RELEASE/SECURITY/LAUNCH، یادداشت حاشیه «چرا انتخاب شده»، لینک منبع با کپی یک‌کلیک، نوار پیشرفت مطالعه، کنترل اندازه فونت، استایل چاپ/PDF، تخمین زمان خواندن، و دکمه **ارسال به تلگرام** برای هر گزارش آرشیو
- `Esc` برای بازگشت به میز
- مانیفست و آیکون وب‌اپ_INCLUDE شده — از منوی مرورگر به‌عنوان پنجره مستقل نصب کنید
- توگل تم ink/paper (تیره/روشن) در هدر، در هر مرورگر به‌صورت جداگانه ذخیره می‌شود

**API محلی** (برای اسکریپت‌نویسی):

| اندپوینت | متد | هدف |
|----------|-----|------|
| `/api/state` | GET | فلگ در حال اجرا، موضوع جاری، آخرین گزارش، برچسب مدل، خطوط لاگ اخیر |
| `/api/run` | POST | شروع ران (`topic`, `dev`, `weekly`, `language`, `max_columns`, `max_news`, `allow_repeats`); `409` اگر در حال اجرا باشد |
| `/api/reports` | GET | کاتالوگ تمام گزارش‌های تولیدشده |
| `/reports/<name>` | GET | سرو فایل یک گزارش (محافظت شده به دایرکتوری خروجی) |
| `/api/settings` | GET / POST | خواندن یا ذخیره تنظیمات مدل/گردش‌کار (نوشتن `settings.overrides.json` + کلید `.env`) |
| `/api/settings/test` | POST | بررسی اتصال زنده به ارائه‌دهنده |

پنل فقط به `127.0.0.1` بایند می‌شود — از شبکه قابل دسترس نیست.

---

## پیکربندی

### مرجع SETTINGS.yaml

همه کلیدها حروف بزرگ یا کوچک می‌پذیرند..placeholderهای `${VAR}` / `${ENV.VAR}` از محیط و `.env` تحلیل می‌شوند.

| بخش | کلیدها | کنترل می‌کند |
|-------|--------|--------------|
| `DEBUG` | `bool` | لاگ‌کردن مفصل |
| `TOPICS` | `list[str]` | موضوعات مورد استفاده `--all` |
| `PROXY` | `url` | پراکسی مشترک برای مدل/جست‌وجو/مرور (هر بخش می‌تواند override کند) |
| `MODEL` | `preset` **یا** `provider`, `base_url`, `model`, `model_type`, `auth.api_key`, `request_options` | اندپوینت LLM و گزینه‌های نمونه‌برداری (مثلا `temperature`, `extra_body`) |
| `SEARCH` | `max_results`, `timelimit` (`d`/`w`/`m`), `region` (`us-en`, `cn-zh`...), `backend` (`auto`/`bing`/`duckduckgo`/`yahoo`/`google`/`yandex`/...), `rss_feeds`, `proxy` | رفتار موتور جست‌وجو و استخر کاندیدای RSS اضافه |
| `BROWSE` | `enable_playwright`, `playwright_headless`, `enable_jina_fallback`, `response_mode` (`markdown`/`text`), `max_content_length`, `min_content_length`, `proxy` | واکشی صفحه و استخراج محتوا |
| `WORKFLOW` | `max_column_num`, `max_news_per_column`, `output_language`, `tone` (`editorial`/`conversational`), `column_concurrency`, `summary_concurrency` | شکل گزارش، لحن، و موازی‌سازی |
| `OUTLINE` | `use_customized`, `customized.report_title`, `customized.column_list[]` (`column_title`, `column_requirement`, `search_keywords`) | رد کردن تولید سرفصل توسط LLM و استفاده از سرفصل ثابت |
| `OUTPUT` | `directory`, `formats` (`markdown`/`json`/`html`), `update_index`, `update_dashboard` | کجا و چگونه گزارش‌ها ذخیره شوند |
| `SUMMARY` | `enable_tldr` | بلوک نکات کلیدی در بالای هر گزارش |
| `DEV_PULSE` | به [نبض برنامه‌نویس](#نبض-برنامه‌نویس-dev) مراجعه کنید | منابع و آستانه‌ها برای `--dev` |
| `HISTORY` | `enabled`, `retention_days`, `path` | حافظه تازگی در اجراهای متوالی |
| `DELIVERY` | `telegram.{enabled, bot_token, chat_id, send_html_file}`, `webhook.{enabled, url}` | куда گزارش‌های تمام‌شده ارسال می‌شوند |

لودر تنظیمات سازگاری پایه با کلیدهای قدیمی v3 را هم حفظ می‌کند (`MODEL_PROVIDER`, `MODEL_URL`, `MODEL_AUTH`, `MODEL_OPTIONS`, `MAX_COLUMN_NUM`, `USE_CUSTOMIZE_OUTLINE`).

### پیش‌تنظیم‌های مدل

`MODEL.preset` به یک بلوک ارائه‌دهنده کامل گسترش می‌یابد — شما فقط کلید API را می‌دهید:

| پیش‌تنظیم | کلید `.env` | مدل پیش‌فرض |
|----------|-------------|--------------|
| `openai` | `OPENAI_API_KEY` | `gpt-4.1-mini` |
| `openrouter` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| `together` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |
| `ollama` | — (لوکال، بدون کلید) | `qwen2.5:7b` @ `localhost:11434` |

`AGENTLY_NEWS_MODEL` را در `.env` ست کنید (یا `model:` در YAML) تا مدل پیش‌فرض پیش‌تنظیم override شود. پیش‌تنظیم‌های ابری در صورت نبودن کلید با خطای شفاف fail-fast می‌کنند؛ `ollama` هرگز کلید نیاز ندارد.

### متغیرهای محیطی (`.env`)

یک `.env` لوکال کنار پروژه (یا کنار exe) در استارت لود می‌شود — متغیرهای محیطی موجود **هرگز override نمی‌شوند**.

| متغیر | استفاده |
|--------|--------|
| `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `TOGETHER_API_KEY` | کلیدهای API پیش‌تنظیم‌ها |
| `AGENTLY_NEWS_MODEL` | override مدل پیش‌فرض پیش‌تنظیم |
| `CUSTOM_API_KEY` | کلید API برای گزینه «custom» پنل |
| `GITHUB_TOKEN` | اختیاری — محدودیت API گیت‌هاب در حالت dev را از ۶۰ به ۵۰۰۰ req/h بالا می‌برد |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | تحویل تلگرام |
| `NEWS_WEBHOOK_URL` | تحویل وب‌هوک |
| `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL`, `DEEPSEEK_API_KEY` | ارجاع داده شده در بلوک پیشرفته مدل نمونه `SETTINGS.yaml` |

### settings.overrides.json

پنل وب **هرگز `SETTINGS.yaml` را ویرایش نمی‌کند**. در عوض یک فایل جانبی `settings.overrides.json` کنارش می‌نویسد، که قبل از تحلیل env روی YAML پارس‌شده overlay می‌شود — بنابراین کامنت‌ها و فرمت YAML شما باقی می‌ماند. وقتی override `MODEL.preset` ست کند، بلوک پایه `MODEL` جایگزین می‌شود (فقط `request_options` نگه‌داشته می‌شود) تا placeholderهای قدیمی `base_url`/`auth` نتوانند پیش‌تنیم را سایه بزنند. فایل را حذف کنید تا به `SETTINGS.yaml` خالی برگردید.

---

## تحویل: تلگرام و وب‌هوک

### تلگرام

1. با [@BotFather](https://t.me/BotFather) ربات بسازید و توکن را کپی کنید.
2. چت‌آیدی خود را پیدا کنید (مثلا به [@userinfobot](https://t.me/userinfobot) پیام دهید).
3. به `.env` اضافه کنید:
   ```dotenv
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_CHAT_ID=123456789
   ```
4. `DELIVERY.telegram.enabled: true` در `SETTINGS.yaml` ست کنید. هر ران سپس یک پیام خلاصه فشرده به‌علاوه گزارش HTML مستقل به‌عنوان ضمیمه می‌فرستد (`send_html_file: false` برای غیرفعال کردن ضمیمه).

**پست‌های کانال‌مانند**: `send_style: channel` ست کنید — پست تیترهای باز، سپس یک پست برای هر داستان (با عکس در صورت وجود)، سپس پست آمار پایانی. `send_style: digest` پیام‌های فشرده چندداستانه قدیمی را نگه می‌دارد.

### وب‌هوک

`NEWS_WEBHOOK_URL` را در `.env` و `DELIVERY.webhook.enabled: true` ست کنید — هر گزارش تمام‌شده به‌عنوان JSON (`title`, `takeaways`, `columns`, `markdown`) به آن URL POST می‌شود، آماده برای پل‌های Slack/Discord، جریان‌های n8n/Zapier، یا سرویس خودتان.

**خطاهای تحویل لاگ می‌شوند اما هرگز ران را متوقف نمی‌کنند** — گزارش شما همیشه اول لوکال ذخیره می‌شود.

---

## خروجی‌ها و داشبورد

هر ران در `OUTPUT.directory` (پیش‌فرض `./outputs`) می‌نویسد:

| فایل | توضیح |
|------|-------------|
| `<title>_<date>.md` | گزارش Markdown (همیشه نوشته می‌شود) |
| `<title>_<date>.json` | داده ساختاری کامل، مورد استفاده `--rerender` و `--weekly` |
| `<title>_<date>.html` | صفحه استایل‌دهی شده مستقل، بدون وابستگی خارجی |
| `INDEX.md` | ایندکس Markdown تمام گزارش‌ها (`OUTPUT.update_index`) |
| `index.html` + `reports.json` | داشبورد/کاتالوگ مرورپذیر تمام گزارش‌ها (`OUTPUT.update_dashboard`) |
| `.history.json` | حافظه داستان‌های منتشرشده برای تازگی (`HISTORY`، پیش‌فرض ۳۰ روز retention) |
| `.trends.json` | حافظه استریک روند برای نبض برنامه‌نویس |
| `feed.xml` | فید RSS تمام گزارش‌ها |

چون هر گزارش JSON خود را نگه می‌دارد، `python app.py --rerender` می‌تواند همه فایل‌های HTML/Markdown را با طراحی کنونی در هر لحظه بازسازی کند — بلافاصله و بدون هیچ فراخوانی LLM.

---

## انتشار خودکار روزانه

مخزن شامل گردش‌کارهای GitHub Actions است (در فورک خود تحت `.github/workflows/` اضافه کنید):

### `daily.yml` — نبض برنامه‌نویس روزانه + GitHub Pages

هر صبح نبض برنامه‌نویس را اجرا می‌کند و `outputs/` را روی **GitHub Pages** منتشر می‌کند — داشبورد، گزارش‌ها، و فید RSS شامل.

**برای فعال‌سازی در فورک:**

1. تنظیمات ریپو **Settings → Pages** → Source: **GitHub Actions**.
2. **Settings → Secrets and variables → Actions** → اضافه کنید:
   - `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_DEFAULT_MODEL`
   - (یا `SETTINGS.yaml` را ویرایش کنید تا از پیش‌تنظیم تک‌کلید `preset:` استفاده کند).
3. برای برنامه زمان‌بندی صبر کنید یا گردش‌کار را به‌صورت دستی از تب Actions اجرا کنید.

### `release.yml` — ساخت فایل اجرای ویندوز

تگ ریلیز (`git tag v1.1.0 && git push --tags`) گردش‌کار ریلیز را راه‌اندازی می‌کند، که exe ویندوز را با PyInstaller می‌سازد و به ریلیز گیت‌هاب ضمیمه می‌کند.

---

## ساخت فایل اجرای مستقل ویندوز

ترجیحی — از spec موجود بسازید (قبلاً شامل اصلاح hook و باندل `SETTINGS.yaml`، `prompts/`، و `webui/` است):

```bash
pip install pyinstaller
pyinstaller DailyNewsCollector.spec --noconfirm
```

یا دستور معادل صریح:

```bash
pyinstaller --onefile --name DailyNewsCollector \
  --add-data "SETTINGS.yaml;." --add-data "prompts;prompts" \
  --add-data "webui;webui" \
  --collect-all agently --collect-all ddgs \
  --additional-hooks-dir packaging/hooks --noconfirm app.py
```

> `--additional-hooks-dir packaging/hooks` الزامی است: یک hookِ pyinstaller-hooks-contrib برای پکیج PyPI نامربوط `workflow` را override می‌کند که با پکیج لوکال `workflow` این پروژه تداخل دارد.

نتیجه `dist/DailyNewsCollector.exe` است. در اولین اجرا یک `SETTINGS.yaml` و `prompts/` پیش‌فرض کنار خودش استخراج می‌کند تا قابل ویرایش باشند؛ `outputs/`، `logs/`، و تاریخچه هم کنار exe می‌مانند. یک `.env` کنار exe برای اعتبار مدل/تلگرام بگذارید، بعد:

```powershell
DailyNewsCollector.exe                # دوکلیک = پنل وب باز می‌شود
DailyNewsCollector.exe "AI agents" --quiet
DailyNewsCollector.exe --all          # همه موضوعات در TOPICS
DailyNewsCollector.exe --dev          # نبض برنامه‌نویس
```

---

## داکر

یک [`Dockerfile`](Dockerfile) مینیمال شامل است (پایه Python 3.10، `pip install -r requirements.txt`, `CMD python app.py`):

```bash
docker build -t agently-news .
docker run --rm -it --env-file .env \
  -v "$PWD/outputs:/app/outputs" agently-news \
  python app.py "AI agents" --quiet
```

`outputs/` را مانت کنید تا گزارش‌ها و تاریخچه روی میزبان بماند. ایمیج CLI را اجرا می‌کند؛ به‌صورت پیش‌فرض پورت پنل را expose نمی‌کند.

---

## ساختار پروژه

```text
.
├── app.py                     # نقطه ورودی نازک -> news_collector.cli.main
├── SETTINGS.yaml              # تمام پیکربندی (مدل، جست‌وجو، گردش‌کار، تحویل، ...)
├── requirements.txt           # agently>=4.0.8.3, PyYAML, ddgs, beautifulsoup4, python-dotenv, httpx, jdatetime
├── Dockerfile
├── DailyNewsCollector.spec    # Spec پای‌اینستالر
├── news_collector/            # لایه app / یکپارچه‌سازی
│   ├── cli.py                 #   argparse CLI، مدیریت frozen-exe، dispatch
│   ├── config.py              #   مدل تنظیمات، پیش‌تنظیم مدل، تحلیل env، merge overrides
│   ├── collector.py           #   DailyNewsCollector: اتصال مدل + ابزارها + flow، اجرا collect(topic)
│   ├── dev_pulse.py           #   سرفصل نبض برنامه‌نویس + جهش تنظیمات
│   ├── weekly.py              #   تولید خلاصه هفتگی از JSON گزارش‌های ذخیره‌شده
│   ├── history.py             #   حافظه تازگی (.history.json)
│   ├── delivery.py            #   پُش تلگرام + وب‌هوک
│   ├── markdown.py            #   رندر Markdown + برچسب‌های بومی‌سازی‌شده
│   ├── html_report.py         #   طراحی گزارش HTML مستقل
│   ├── dashboard.py           #   کاتالوگ outputs/index.html + reports.json
│   ├── rerender.py            #   پیاده‌سازی --rerender
│   ├── webui.py               #   سرور HTTP پنل کنترل محلی + اندپوینت‌های /api
│   ├── webui_html.py          #   پنل فول‌بک خطی (وقتی webui/ وجود نداشته باشد)
│   └── logging_utils.py       #   کنسول + logs/collector.log
├── workflow/                  # ارکستریشن TriggerFlow
│   ├── daily_news.py          #   flow والد + sub flow ستون + sub flow خلاصه‌سازی
│   ├── report_chunks.py       #   آماده‌سازی درخواست، سرفصل، TL;DR، deduplicate، نوشتن خروجی‌ها، تاریخچه
│   ├── column_chunks.py       #   جست‌وجو/گزینش/نگارش ستون با فول‌بک‌ها
│   ├── summary_chunks.py      #   مرور + خلاصه‌سازی کاندیدا، مسیریابی پرامپت مخصوص نوع
│   └── common.py              #   کانفیگ chunk، ایجنت‌های ویراستار، کمک‌های لحن/زبان
├── tools/                     # لایه آداپتور قابل‌پلاگین (tools/README.md)
│   ├── base.py                #   پروتکل‌های Search/Browse
│   ├── builtin.py             #   wrapperهای Agently v4 Search/Browse + فول‌بک Jina
│   ├── rss.py                 #   استخر کاندیدای RSS/Atom
│   ├── dev_sources.py         #   کانال‌های GitHub/HN/Reddit/Lobsters/dev.to/daily.dev/Product Hunt + استریک روند
│   └── content_quality.py     #   تشخیص محتوای نامعتبر (captcha، paywall، ...)
├── prompts/                   # قراردادها پرامپت ساختاریافته (YAML قابل ویرایش)
│   ├── create_outline.yaml    #   طراحی سرفصل گزارش
│   ├── pick_news.yaml         #   میان‌بر کردن کاندیداها در هر ستون
│   ├── summarize_news.yaml    #   خلاصه‌سازی مقاله مرورشده
│   ├── summarize_repo.yaml    #   معرفی مخزن گیت‌هاب به‌شکل گفتگوماند
│   ├── summarize_release.yaml #   چه‌چیزی تغییر کرد / breaking / آپگرید یا صبر
│   ├── summarize_advisory.yaml#   هشدار مشورتی امنیتی
│   ├── write_column.yaml      #   ستون نهایی + مقدمه
│   ├── write_tldr.yaml        #   نکات کلیدی
│   └── write_weekly.yaml      #   مرور هفته + هایلایت‌ها
├── webui/                     # پنل کنترل — یک فایل HTML خودمحتوایی، بدون بیلد
├── packaging/hooks/           # اصلاح hook پای‌اینستالر برای تصادف نام `workflow`
├── outputs/                   # گزارش‌ها، داشبورد، INDEX.md، .history.json، .trends.json
└── logs/                      # collector.log
```

---

## معماری

کل ران یک `TriggerFlow` Agently v4 با دو sub flow تو در تو است:

```
flow والد   prepare_request → generate_outline → for_each(column) → render_report
flow ستون   search → pick → summarize → write_column
flow خلاصه  for_each(داستان برگزیده) → browse → summarize   (fan-out موازی)
```

### ویژگی‌های Agently v4 استفاده‌شده

| ویژگی | نحوه استفاده در این پروژه |
|---------|--------------------------|
| **ارکستریشن TriggerFlow** | جایگزین سبک قدیمی workflow v3 با گراف flow صریح (`to`, `for_each`, `sub flow`, ترکیب branching-ready). ستون‌ها به‌صورت موازی اجرا می‌شوند و خلاصه‌سازی داستان‌های برگزیده در هر ستون هم موازی است. |
| **ترکیب Sub flow** | «ساخت یک ستون» به TriggerFlow مستقل استخراج شده و از flow والد در `for_each(column)` بارها فراخوانی می‌شود. والد روی ارکستریشن سطح گزارش متمرکز می‌ماند؛ فرزند قابل تست، بصری‌سازی، و export مستقل. انواع آینده (ستون خلاصه، ستون deep-dive، ستون منطقه‌ای) می‌توانند از child flow reuse یا derive کنند. |
| **قراردادهای خروجی ساختاریافته** | پرامپت‌های YAML اسکیمای خروجی را مستقیماً برای تولید سرفصل، گزینش خبر، خلاصه‌سازی، و نگارش ستون تعریف می‌کنند. گلو significativamente کمتر، اینترفیس‌های rõ بین گام‌ها، iteration پرامپت آسان‌تر. |
| **ابزارهای داخلی Search / Browse** | پیش‌فرض از پیاده‌سازی‌های داخلی Agently v4 استفاده می‌کند به‌جای helperهای پروژه قدیمی. کاربران همچنان می‌توانند از طریق `./tools` پیاده‌سازی را swap کنند بدون بازنویسی workflow. |
| **منابع اجرا و فضاهای نام state** | منابع اجرا TriggerFlow برای تزریق وابستگی logger/search/browse استفاده می‌شوند؛ state اجرا داده‌های اجرا (درخواست، سرفصل، نتایج میانی) را نگه می‌دارد. وایرینگ وابستگی و state اجرا به‌شکل تمیز جدا شده‌اند، کد chunkها لاغر. |
| **تنظیمات آگاه از محیط** | `set_settings(..., auto_load_env=True)` Agently v4 مستقیماً با placeholderهای `${ENV.xxx}` کار می‌کند. اندپوینت مدل، نام مدل، و کلید API قابل تغییر از محیط هستند بدون ویرایش کد یا commit Geheimnis. |

### اثر کلی

- رفتار محصول اصلی برای کاربران v3 آشنا باقی مانده، اما پروژه اکنون split تمیز `app/workflow/tools/prompts` دارد.
- منطق بیشتری در قابلیت‌های بومی Agently بیان شده به‌جای کد گلو پروژه‌ای.
- موازی‌سازی واقعی اکنون بخش پیش‌فرض مدل اجرا است (v3 به‌شکل موثر serial بود).
- جایگزینی ابزارها، تنظیم پرامپت‌ها، یا تکامل گام‌های workflow ریسک کمتر از layout قدیمی v3 دارد.
- تکامل workflow می‌تواند به لایه باشد: تغییرات سطح گزارش در flow والد، تغییرات سطح ستون در sub flow، به‌جای مجبور کردن هر دو به تغییر هم‌زمان.

---

## تغییرات مهم v3 → v4

زنجیره کسب‌وکار همچنان به‌شکل تقریبی است:

```
سرفصل → جست‌وجو → گزینش → مرور + خلاصه‌سازی → نگارش ستون → رندر markdown
```

تغییر شکل مهندسی اطراف آن زنجیره است.

### تغییرات سطح پروژه

- پروژه قدیمی v3 از یک workflow اصلی به‌علاوه workflow ستون تو در تو تحت `./workflows`، با helperهای سفارشی `search.py` / `browse.py` و پاس‌دادن state سبک storage استفاده می‌کرد.
- پروژه v4 مسئولیت‌ها را تمیزتر جدا می‌کند:
  - `news_collector/`: لایه app/integration
  - `workflow/`: flow والد، sub flow ستون، و منطق chunk واقعی
  - `tools/`: لایه آداپتور جست‌وجو/مرور
  - `prompts/`: قراردادها پرامپت ساختاریافته
- پیکربندی مدل دیگر در پایتون hardcode نیست. اکنون از placeholderهای `${ENV.xxx}` در `SETTINGS.yaml` استفاده می‌کند، بنابراین استقرار و سوییچ لوکال ساده‌ترند.
- وایرینگ ابزارها دیگر در کد workflow دفن نیست. جست‌وجو، مرور، و logger به‌عنوان منابع اجرا TriggerFlow inject می‌شوند، که workflow را جایگزین/تست‌پذیرتر می‌کند.
- برنامه workflow اکنون نزدیک‌تر به مرز کسب‌وکار است:
  - flow والد: `prepare_request → generate_outline → for_each(column) → render_report`
  - sub flow ستون: `search → pick → summarize → write_column`
  - گام `summarize` درون flow ستون بیشتر به یک sub flow خلاصه‌سازی đẩy شده، جایی که TriggerFlow مستقیماً fan-out و collection را هندل می‌کند به‌جای رها کردن `asyncio.gather` در کد بزنسی
  - این والد را روی ارکستریشن گزارش و فرزند را روی چرخه حیات یک ستون متمرکز نگه می‌دارد
  - ارزش فوری `sub flow` اینجاست که پایپ‌لاین ستون به یک واحد workflow قابل reuse و به‌صورت مستقل evolvable تبدیل می‌شود به‌جای ماندن دفن در یک chunk والد oversized

---

## نکات

- Python `>=3.10` الزامی است چون Agently v4 آن را نیاز دارد.
- این پروژه Agently `>=4.0.8.3` می‌طلبد.
- تنظیمات مدل از placeholderهای `${ENV.xxx}` تحلیل شده از محیط / `.env` (Agently v4 `auto_load_env=True`) استفاده می‌کند، یا میانبر ساده‌تر `MODEL.preset`.
- `tools/` پیش‌فرض از پیاده‌سازی‌های بومی Agently v4 استفاده می‌کند، اما می‌توانید factoryها را با ابزارهای خودتان جایگزین کنید (به [`tools/README.md`](tools/README.md) مراجعه کنید).
- `workflow/` بر اساس مرز بزنسی به flow والد، sub flow ستون، chunkهای سطح گزارش، و chunkهای سطح ستون شکافته شده.
- `news_collector/` به‌عنوان لایه app/integration برای پیکربندی، وایرینگ مدل، CLI، پنل وب، رندر، و تحویل عمل می‌کند.
- نمونه [`SETTINGS.yaml`](SETTINGS.yaml) با `BROWSE.enable_playwright: false` و `enable_jina_fallback: true` जहاز می‌شود؛ Playwright را برای کیفیت مرور بهتر در سایت‌های خبری پویا یا محافظت‌شده فعال کنید (`pip install playwright && playwright install chromium`).
- پرامپت CLI تعاملی دوزبانه است (انگلیسی/چینی)؛ UI پنل وب فارسی/RTF-first است؛ گزارش‌ها خود `WORKFLOW.output_language` را دنبال می‌کنند.
- README چینی پروژه اصلی در [`README_CN.md`](README_CN.md) موجود است (ممکن است از این فایل قدیمی‌تر باشد).

---

## مجوز

[Apache 2.0](LICENSE)