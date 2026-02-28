# Daily Audio Briefing — Project CLAUDE.md

Desktop Python/Tkinter app that creates personalized audio news briefings from YouTube channels, newsletters, and RSS feeds. Uses Google Gemini API for AI summarization, gTTS (fast) and Kokoro ONNX (quality) for text-to-speech. Packaged for distribution via PyInstaller (macOS .dmg, Windows .exe).

## Key Files

All source files are in `daily_audio_briefing/`.

| File | Lines | Purpose |
|------|-------|---------|
| `gui_app.py` | ~8800 | **Main GUI — NEVER read in full.** Sidebar nav + 7 pages (Home, Summarize, Extract, Audio, Scheduler, Settings, Guide). Use grep for targeted searches. |
| `cloud_scheduler_client.py` | ~175 | REST API client for remote scheduler (Render server) |
| `data_csv_processor.py` | ~2100 | Data extraction and Grid enrichment |
| `source_fetcher.py` | ~1600 | Unified content fetching (YouTube, RSS, article archives) |
| `execsum_processor.py` | ~870 | ExecSum newsletter processing |
| `scheduler_daemon.py` | ~610 | Background daemon for scheduled tasks |
| `get_youtube_news.py` | ~580 | YouTube video fetching and AI summarization |
| `source_processor.py` | ~440 | Unified source routing |
| `scheduler.py` | ~720 | Automated task scheduler — extraction + briefing pipeline (Sheets persistence, deferred loading) |
| `audio_generator.py` | ~380 | Audio generation orchestration |
| `make_audio_quality.py` | ~210 | Kokoro TTS high-quality audio |
| `sheets_manager.py` | ~350 | Google Sheets export, tab management, deduplication |
| `file_manager.py` | ~155 | File I/O with frozen app support |
| `api_usage_tracker.py` | ~420 | Gemini API call tracking, daily/monthly limits, dollar budget cap, cooldown mode, cost estimation |
| `web_app.py` | ~2850 | Flask web dashboard (scheduler, extraction, audio) — **NEVER read in full.** Use grep. |
| `server_scheduler.py` | ~80 | Flask-integrated scheduler for cloud deployment |

Config files: `sources.json` (gitignored, copy from `sources.example.json`), `instruction_profiles.json`, `scheduled_tasks.json`, `settings.json`
Extraction configs: `extraction_instructions/*.json` (execsum, rwa, cryptosum, _template)

## Dual-Mode Architecture

**Frozen (PyInstaller) mode:**
- Config files READ from bundle (`sys._MEIPASS`), WRITTEN to data dir
- Output goes to `~/Library/Application Support/Daily Audio Briefing/`
- Scripts run IN-PROCESS via import, not subprocess

**Development mode:**
- All files read/write from script directory (`os.path.dirname(__file__)`)
- Scripts run via subprocess
- Launch with: `Launch Audio Briefing.command`

## Source Processing Pipeline

- `sources.json`: Schema v2.0 with `type` (youtube|newsletter|rss) and `config` fields
- `source_processor.py`: Loads sources, detects types, routes to appropriate processors
- `extraction_instructions/*.json`: Per-source config with include/exclude patterns, capabilities
- `_template.json`: Documented template for creating new extraction configs

### Capabilities System
Configs enable advanced features via `capabilities` field:
- `csv_export`: CSV output with custom columns
- `grid_enrichment`: Grid/database integration
- `research_articles`: Deep article fetching
- `custom_prompts`: Custom AI extraction prompts

Consumer builds ship with capabilities disabled. Power users enable as needed.

## Config-Based URL Detection

URLs pasted in the audio content textbox are checked against extraction configs:
1. `_categorize_urls_by_config()` checks article URLs against config domains
2. Matched URLs show blue banner with "Extract Data" button
3. "Extract Data" uses Data Extractor logic (filtering, patterns) instead of AI summarization

**Domain mapping** (in `gui_app.py` `_load_extraction_configs()`):
- execsum.co -> execsum.json
- cryptosum.beehiiv.com -> cryptosum.json
- rwaxyz.com -> rwa.json

To add new mappings: add `source_url_patterns` field to config JSON, or update `domain_map` dict.

## Navigation Architecture (Desktop App)

The desktop app uses a **sidebar + page container** layout matching the web app:

```
┌──────────────┬─────────────────────────────────┐
│  Sidebar     │  Page Container                  │
│  (200px)     │  (CTkScrollableFrame per page)   │
│              │                                   │
│  🏠 Home     │  Only one page visible at a time │
│  📰 Summarize│  via grid()/grid_remove()        │
│  📊 Extract  │                                   │
│  🔊 Audio    │                                   │
│  📅 Scheduler│                                   │
│  ⚙️ Settings │                                   │
│  📖 Guide    │                                   │
└──────────────┴─────────────────────────────────┘
```

**Key methods:** `_create_sidebar()`, `_create_pages()`, `_navigate_to(page_name)`
**Color tokens:** `COLORS` dict at module level (matches web app CSS variables)
**Card factory:** `_create_card(parent, title)` — consistent card styling across all pages

**Scheduler modes:** Local (embedded `Scheduler` class) or Cloud (`CloudSchedulerClient` REST wrapper). Switched via segmented button on Scheduler page. `_get_active_scheduler()` returns the active backend.

## Do NOT
- Break the working development mode (`Launch Audio Briefing.command`)
- Change the output folder structure (`Week_N_YYYY` format)
- Remove any existing functionality
- Read `gui_app.py` in full (~8800 lines) — always use grep/targeted reads
- Commit `.env`, `google_credentials.json`, or API keys

## Server Deployment (Render.com)

> **Note:** Render server is currently suspended due to budget constraints. Desktop app is the primary interface.

The web dashboard (`web_app.py`) includes a Scheduler page for managing automated feed→Sheets tasks.
Deploy to Render.com free tier with keep-alive ping to prevent sleep.

**Key server files:**
- `web_app.py` — Flask app with scheduler dashboard, API endpoints, live preview
- `server_scheduler.py` — Flask-integrated scheduler wrapper (runs as background thread)
- `requirements-server.txt` — Server-only dependencies (no GUI/audio)
- `render.yaml` — Render.com deployment config

**Environment variables (set in Render dashboard):**
- `SERVER_MODE=true` — Enables auto-start of scheduler
- `GEMINI_API_KEY` — For AI summarization
- `GOOGLE_CREDENTIALS_JSON` — Full JSON of service account credentials (for Sheets)
- `SCHEDULER_SHEET_ID` — Spreadsheet ID for task persistence across redeploys

**Keep-alive:** Self-ping built in (pings `/health` every 4 min) + UptimeRobot as backup.

**Render constraints & mitigations:**
- 512MB RAM limit → `yt-dlp` removed from server deps, server mode uses `max_workers=2`, `resolve_redirects=False`
- Ephemeral filesystem → tasks persist to Google Sheets (`_scheduler_config` tab), 3-tier fallback: file → Sheets → env var
- 120s worker timeout → `Scheduler.load_tasks()` deferred to background thread in server mode (Sheets API auth takes 4+ min on cold start)
- `render.yaml` startCommand changes not auto-applied after initial creation → must also update in Render Dashboard → Settings

**Start command (must match both render.yaml and Render Dashboard):**
```
gunicorn web_app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --preload
```

## Current Status

**Alpha testing.** Users must provide their own API keys and Google credentials (no admin keys in repo). The web dashboard is open (no auth). Render server is suspended; desktop app is the primary interface.

**Distribution:** Users clone from GitHub, copy `.env.example` → `.env`, add their own Gemini API key.

## Pending Work

**High Priority:**
1. ~~Rebuild macOS app~~ ✅ Rebuilt with all UX fixes + custom icons (Feb 2026)
2. Test multi-URL feature in GUI
3. ~~Commit outstanding changes~~ ✅ Merged `server-deploy` → `main`, pruned stale branches
4. ~~Deploy to Render.com~~ ✅ Live at https://news-summarizer-zgny.onrender.com
5. ~~Add Guide page, tooltips, alpha banner~~ ✅ Done
6. ~~Update README with web dashboard and server docs~~ ✅ Done
7. ~~Fix config name mapping (display_name vs filename)~~ ✅ Done
8. ~~Desktop app redesign — sidebar nav + 7 pages matching web app~~ ✅ Done
9. ~~Cloud scheduler client — desktop connects to Render server~~ ✅ Done
10. ~~Web app desktop-only badges + download guide~~ ✅ Done
11. ~~First-run wizard + versioning~~ ✅ APP_VERSION, dependency checklist, privacy note
12. ~~Roadmap (desktop Guide, web Guide, README)~~ ✅ 4-phase roadmap
13. ~~Custom app icons~~ ✅ AppIcon.icns/ico from news_summarizer_favicons PNGs

**Desktop UX (completed Feb 2026):**
- ~~Frozen app not clickable~~ ✅ NSPrincipalClass + hook-tk-fix.py + settings path fix
- ~~Calendar click-through~~ ✅ transient/grab_set/lift/topmost
- ~~Window minimum size~~ ✅ minsize(850, 650)
- ~~Navigation speed~~ ✅ Cached ffmpeg (background pre-warm), deferred scheduler init, update_idletasks
- ~~Mouse scroll wheel~~ ✅ _bind_page_mousewheel() for CTkScrollableFrame on macOS
- ~~Cached text reappearing~~ ✅ Removed load_current_summary() from on_toggle_range()
- ~~Setup wizard buttons cut off~~ ✅ Increased geometry to 550x620

**Server/Infra:**
- ~~Set up UptimeRobot keep-alive ping~~ ✅ Self-ping built-in + UptimeRobot
- ~~Test Sheets export via env var credentials~~ ✅ Working
- Verify web app feature parity with desktop version
- ~~Persistent storage (tasks lost on redeploy)~~ ✅ Google Sheets persistence with 3-tier fallback
- ~~Fix Render OOM crashes~~ ✅ Fixed lock contention, task mutex, gc.collect(), 10MB cap, memory monitoring
- ~~Fix worker timeout on cold start~~ ✅ Deferred load_tasks() to background thread
- ~~Sheet tab rename detection~~ ✅ Auto-resolves renamed tabs
- ~~Sheet tab validation + create-tab in web UI~~ ✅ Blue checkmark / amber warning
- ~~Inline config editor in scheduler~~ ✅ Edit columns, patterns, blocked domains
- ~~Auto-dismiss notifications~~ ✅ 5s timeout for success/info
- ~~Favicon serving on Render~~ ✅ Dedicated Flask routes
- ~~Memory leak mitigations~~ ✅ Task TTL eviction (1hr/100 cap), Sheets service caching, GC in self-ping + after subprocess, memory watchdog (450MB warn, 480MB restart), template extraction to Jinja2
- Slow memory leak on free tier — ~2.4MB/hour, OOM every ~12-24h. Service auto-recovers via watchdog. Consider plan upgrade.

**Scheduler Capabilities (completed Feb 2026):**
- ~~Cryptosum scheduled task~~ ✅ Daily extraction from cryptosum.beehiiv.com → Google Sheets
- ~~Grid enrichment in scheduler~~ ✅ `enrich_with_grid` flag on ScheduledTask, runs in _execute_task()
- ~~Research articles in scheduler~~ ✅ `research_articles` flag on ScheduledTask, ecosystem mention detection
- ~~Task editor capabilities UI~~ ✅ Checkboxes for Grid/Research in task editor dialog
- ~~Capability badges in task list~~ ✅ Shows [Grid + Research] badges on task rows

**Roadmap — Web App Scheduler:**
- Port scheduler capabilities UI to web dashboard
- Unified local+cloud task management in web UI
- Re-enable Render deployment when budget allows

**API Cost Protection (completed Feb 2026):**
- ~~API usage rate limiter~~ ✅ `api_usage_tracker.py` with daily/monthly hard caps, `APILimitExceeded` exception
- ~~User-configurable spending limit~~ ✅ Settings page UI with limit entries, enable/disable switch
- ~~Per-task API call tracking~~ ✅ Thread-local task context in scheduler, per-task totals in `api_usage.json`
- ~~Dashboard showing API usage~~ ✅ Desktop Settings card + web dashboard panel with progress bars, cost estimates
- ~~Dollar-based budget cap~~ ✅ `monthly_budget_usd` in tracker, `BudgetExceeded` exception, budget progress bar + status in both desktop and web UI
- ~~Cooldown mode~~ ✅ When over budget: pipelines still collect raw data but skip AI summarization (graceful degradation). Configurable via cooldown toggle in Settings.
- ~~Distribution safety~~ ✅ No admin keys in repo, `sources.json` gitignored, `sources.example.json` template, `.env.example` with setup instructions
- Future: desktop notification + email alerts when approaching limits

**Briefing Pipeline (completed Feb 2026):**
- ~~Automated fetch → summarize → audio → Drive pipeline~~ ✅ New `briefing_pipeline` task type on ScheduledTask
- ~~Pipeline executor in scheduler~~ ✅ `_execute_pipeline_task()` — 6-step chain: load sources → SourceFetcher → format_items_for_audio → save text → TTS subprocess → Drive upload
- ~~Desktop task editor~~ ✅ CTkSegmentedButton type selector, conditional field visibility (extraction vs pipeline), voice selector, source filter, Drive folder config
- ~~Web task editor~~ ✅ Type toggle buttons, pipeline fields, [Pipeline] badge on task cards
- ~~Server mode graceful degradation~~ ✅ Skips audio + Drive steps, saves summary text only
- Future: source filter UI in web app, pipeline progress notifications

**High Priority — New Features:**
- Summary quality audit + cross-source deduplication: audit whether custom instructions are followed, add toggle for post-summary processing step to combine/deduplicate similar info across sources

**Pipeline UX Improvements (completed Feb 2026):**
- ~~Drive folder pre-fill~~ ✅ "Use from Settings" button in pipeline task editor when Settings has a folder configured
- ~~Drive folder quick-link~~ ✅ 📁 button on pipeline tasks opens Google Drive folder in browser
- ~~Kokoro voice samples~~ ✅ All 12 voices shown in 3-column grid with radio buttons, descriptions, and individual play buttons
- ~~Pipeline backfill dialog~~ ✅ Date range picker: auto-detect, 7/30/90 days, full archive, or custom date
- ~~Backfill safety warnings~~ ✅ Dynamic warning banner for long-running backfills (90d, full archive)
- ~~Task execution feedback~~ ✅ macOS desktop notifications on task start/complete + status bar updates from any page
- ~~Cryptosum scheduler bug~~ ✅ Root cause: daily tasks with missed run times were pushed to tomorrow. Fixed: catch-up detection runs missed tasks within 10s of daemon start
- ~~Pipeline audio timeout~~ ✅ Root cause: 600s timeout too short for Kokoro TTS (~1s/sentence × 636+ sentences). Fixed: 1800s timeout, Popen with process group kill, sentence count estimate logging, TTS progress prints
- ~~Catch-up race condition~~ ✅ Root cause: load_tasks() every 60s replaced task objects, resetting catch-up next_run before _run_loop could fire. Fixed: reduced catch-up delay from 60s to 10s
- ~~Task-name filenames~~ ✅ Pipeline outputs include sanitized task name + week number (e.g., News_Summarizer_Pipeline_W9_2026-02-24.txt)
- ~~Pipeline sources not found~~ ✅ Root cause: dev mode `FileManager.base_dir` = script dir (no sources.json, gitignored), fell back to `sources.example.json` with placeholder URL. Fixed: added Application Support as fallback in source-loading chain

**Future — Desktop/Web Sync:**
- Login/registration system for cloud features
- API key gating — require auth to use cloud scheduler API
- Bidirectional sync between desktop settings and cloud
- Shared source lists between desktop and web
- Desktop app auto-update mechanism

**Future — Multi-tenant SaaS:**
- Add authentication to web dashboard (currently open)
- Per-client API keys and Sheets credentials
- Task isolation (client A can't see/modify client B's tasks)
- Rate limiting per client
- Progress indicator for multi-URL extraction
- Save/load URL lists for recurring newsletter batches
- Keyboard shortcuts for common actions

## Build Instructions

```bash
cd daily_audio_briefing
python3 build_app.py
# Then close existing app and copy from dist/ to /Applications/
rm -rf "/Applications/Daily Audio Briefing.app"
cp -R "dist/Daily Audio Briefing.app" /Applications/
```

## Development History

See `Ralph.archive.md` at project root for detailed session-by-session history with problem/solution narratives and root cause analysis.
