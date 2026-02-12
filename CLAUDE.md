# Daily Audio Briefing — Project CLAUDE.md

Desktop Python/Tkinter app that creates personalized audio news briefings from YouTube channels, newsletters, and RSS feeds. Uses Google Gemini API for AI summarization, gTTS (fast) and Kokoro ONNX (quality) for text-to-speech. Packaged for distribution via PyInstaller (macOS .dmg, Windows .exe).

## Key Files

All source files are in `daily_audio_briefing/`.

| File | Lines | Purpose |
|------|-------|---------|
| `gui_app.py` | ~8300 | **Main GUI — NEVER read in full.** Use grep for targeted searches. |
| `data_csv_processor.py` | ~2100 | Data extraction and Grid enrichment |
| `source_fetcher.py` | ~1600 | Unified content fetching (YouTube, RSS, article archives) |
| `execsum_processor.py` | ~870 | ExecSum newsletter processing |
| `scheduler_daemon.py` | ~610 | Background daemon for scheduled tasks |
| `get_youtube_news.py` | ~580 | YouTube video fetching and AI summarization |
| `source_processor.py` | ~440 | Unified source routing |
| `scheduler.py` | ~420 | Automated extraction task scheduler |
| `audio_generator.py` | ~380 | Audio generation orchestration |
| `make_audio_quality.py` | ~210 | Kokoro TTS high-quality audio |
| `sheets_manager.py` | ~210 | Google Sheets export |
| `file_manager.py` | ~155 | File I/O with frozen app support |
| `web_app.py` | ~2700 | Flask web dashboard (scheduler, extraction, audio) — **NEVER read in full.** Use grep. |
| `server_scheduler.py` | ~80 | Flask-integrated scheduler for cloud deployment |

Config files: `sources.json`, `instruction_profiles.json`, `scheduled_tasks.json`, `settings.json`
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

## Do NOT
- Break the working development mode (`Launch Audio Briefing.command`)
- Change the output folder structure (`Week_N_YYYY` format)
- Remove any existing functionality
- Read `gui_app.py` in full (~8300 lines) — always use grep/targeted reads
- Commit `.env`, `google_credentials.json`, or API keys

## Server Deployment (Render.com)

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

**Keep-alive:** Set up UptimeRobot (free) to ping `/health` every 5 minutes.

## Current Status

**Alpha testing.** API keys and Google credentials are hardcoded to the admin's accounts. The web dashboard is open (no auth). All costs (Gemini API, Sheets API) are on the admin's billing.

**Live deployment:** https://news-summarizer-zgny.onrender.com (Render.com free tier, `server-deploy` branch)

## Pending Work

**High Priority:**
1. Rebuild macOS app — major features added since last build (scheduler, daemon, newsletter rewrite, audio fixes, UI reorg)
2. Test multi-URL feature in GUI
3. ~~Commit outstanding changes~~ ✅ Pushed to `server-deploy` branch
4. ~~Deploy to Render.com~~ ✅ Live at https://news-summarizer-zgny.onrender.com
5. ~~Add Guide page, tooltips, alpha banner~~ ✅ Done
6. ~~Update README with web dashboard and server docs~~ ✅ Done
7. ~~Fix config name mapping (display_name vs filename)~~ ✅ Done

**Server/Infra:**
8. ~~Set up UptimeRobot keep-alive ping after Render deploy~~ ✅ Self-ping built-in + UptimeRobot
9. Test Sheets export via env var credentials on server
10. Verify web app feature parity with desktop version
11. Persistent storage solution for Render (tasks lost on redeploy)

**Critical — API Cost Protection:**
12. API usage rate limiter — hard cap to prevent unexpected bills from scheduler bursts
13. User-configurable spending limit with warnings (desktop notification + email)
14. Per-task API call tracking and cost estimation
15. Dashboard showing cumulative API usage and remaining budget

**Future — Multi-tenant SaaS:**
16. Add authentication to web dashboard (currently open)
17. Per-client API keys and Sheets credentials
18. Task isolation (client A can't see/modify client B's tasks)
19. Rate limiting per client
20. Progress indicator for multi-URL extraction
21. Save/load URL lists for recurring newsletter batches
22. Keyboard shortcuts for common actions

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
