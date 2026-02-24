# Ralph - Development Rails System
# Purpose: Keep the News Summarizer project focused and trim during development

## Current Focus
- API cost protection and usage tracking
- Security hardening (remaining low-priority items)
- Feature pipeline: Summarize → Audio → Drive

## Recently Completed (Session Feb 23, 2026 — API Cost Protection)

### Summary
Added centralized Gemini API usage tracking, daily/monthly hard caps, per-task attribution, cost estimation, and Settings UI for both desktop and web dashboard. Addresses the "Critical — API Cost Protection" items from CLAUDE.md.

### New File: `api_usage_tracker.py` (~310 lines)
- Thread-safe singleton `APIUsageTracker` with `threading.Lock`
- `tracked_generate(model, prompt, caller)` — wraps `model.generate_content()` with pre-flight limit check + post-call tracking
- `APILimitExceeded` exception raised when daily/monthly cap hit
- Thread-local `set_current_task(id, name)` for scheduler attribution without threading task_id through 4 layers
- Lazy day/month rollover — no background timers, resets on first call of new day
- Cost estimation: `chars / 4 ≈ tokens × model pricing table`
- JSON persistence (`api_usage.json`) with atomic writes via `os.replace()`
- Rolling call log (500 entries), daily history (90 days), per-task totals

### Instrumented 7 Call Sites
All `model.generate_content(prompt)` → `tracker.tracked_generate(model, prompt, caller)`:
- `gui_app.py`: `_clean_article_content()`, `_summarize_youtube_transcript()`, `_process_audio_content_for_summary()`
- `source_fetcher.py`: `_summarize_youtube()`, `_summarize_article()`
- `get_youtube_news.py`: `summarize_text()`
- `grid_api.py`: `analyze_profile_with_ai()`

### Scheduler Integration
Added `set_current_task`/`clear_current_task` in 4 scheduler methods:
- `_execute_task()`, `_run_backfill()`, `_run_reenrich()`, `_run_retitle()`
- All in try/finally blocks ensuring cleanup

### Desktop Settings UI
New "API Usage & Limits" card (row 5) on Settings page:
- Daily/monthly progress bars with call counts
- Cost estimate labels
- Enable/disable limits switch
- Configurable daily + monthly limit entries
- Save Limits + Reset Today buttons
- Per-task breakdown showing scheduler task call counts
- Refreshes on every Settings page visit via `_refresh_settings_page()`

### Web Dashboard
- 4 new API endpoints: `/api/usage/stats`, `/api/usage/history`, `/api/usage/tasks`, `/api/usage/limits`
- Usage stats panel in Settings section with progress bars and per-task breakdown

### Key Files Modified
- `api_usage_tracker.py` — NEW: core tracker module
- `gui_app.py` — 3 call sites + Settings card + refresh/save methods + startup init
- `source_fetcher.py` — 2 call sites wrapped
- `get_youtube_news.py` — 1 call site wrapped
- `grid_api.py` — 1 call site wrapped
- `scheduler.py` — task context in 4 methods (8 insertion points)
- `web_app.py` — 4 new endpoints
- `templates/index.html` — usage stats panel
- `CLAUDE.md` — updated pending work section

---

## Recently Completed (Session Feb 13-17, 2026 — Desktop Rebuild & UX Polish)

### Phase 2: Frozen App Click Fix
- PROBLEM: PyInstaller-built macOS app launched but nothing was clickable
- ROOT CAUSE: Missing `NSPrincipalClass: NSApplication` in Info.plist — macOS never delivered events to the app
- FIX 1: Added `NSPrincipalClass`, `LSApplicationCategoryType`, `LSEnvironment`, `CFBundleURLTypes` to DailyAudioBriefing.spec
- FIX 2: Created `hook-tk-fix.py` runtime hook to fix Tcl/Tk data paths in frozen mode
- FIX 3: Fixed settings path — `get_data_directory()` was returning wrong path for `sys._MEIPASS` mode
- FIX 4: Added `TransformProcessType` call to promote process to foreground app

### Phase 3: 7 UX Issues (all implemented)
1. **Navigation speed** — Added `_cached_check_ffmpeg()` module-level cache + `update_idletasks()` in `_navigate_to()`
2. **Cached text guard** — Added page guard in `_on_textbox_change()` (later found insufficient — fixed properly in Phase 4)
3. **Calendar click-through** — Added `transient()`, `grab_set()`, `lift()`, `topmost`, `resizable(False, False)`, larger geometry
4. **Window minimum size** — `self.minsize(850, 650)`
5. **Web desktop-only badges** — Desktop App badges on voice selector/Play Sample, Download App header button, feature comparison table
6. **First-run wizard** — `_show_first_run_wizard()` modal with dependency checklist (ffmpeg, Kokoro), privacy note, Continue/Skip buttons
7. **Roadmap** — Added to Desktop Guide page, Web Guide page, and README.md (4-phase: Alpha → User Accounts → Full Cloud → SaaS)
- Added `APP_VERSION = "1.0.0-alpha"` constant, sidebar version label

### Phase 4: 4 Remaining UX Fixes
1. **Wizard buttons cut off** — Increased geometry from 550x520 → 550x620
2. **Mouse scroll wheel** — Added `_bind_page_mousewheel()` method binding `<MouseWheel>`, `<Button-4>`, `<Button-5>` to each page's `_parent_canvas`; CTkScrollableFrame on macOS doesn't auto-bind
3. **Cached text STILL reappearing** — Real root cause: `on_toggle_range()` unconditionally called `load_current_summary()` which reloaded `summary.txt` into textbox on every checkbox toggle. Removed those calls from `on_toggle_range()`, moved to one-time init
4. **Slow first-launch** — Deferred `_init_scheduler()` to first Scheduler page visit (lazy-init with `_scheduler_initialized` flag); pre-warmed ffmpeg cache on background daemon thread at module level

### Phase 5: Custom App Icons
- Generated `AppIcon.icns` (31KB) from existing favicon PNGs using `iconutil` — all macOS sizes including @2x Retina
- Generated `AppIcon.ico` (5KB, 6 sizes: 16-256px) using manual PNG-in-ICO format (Pillow's ICO writer was buggy)
- Updated `DailyAudioBriefing.spec` — `icon='AppIcon.icns'` (macOS BUNDLE) and `icon='AppIcon.ico'` (Windows EXE)
- Source PNGs at `/news_summarizer_favicons/` (newspaper + AI sparkle design)

### Server OOM Analysis (Feb 16-17, 2026)
- Render sent memory limit exceeded email — auto-restart triggered
- Metrics showed slow memory leak: ~200KB every 5 min from health checks alone (~2.4MB/hour)
- Baseline after Sheets loading: ~380-460MB; climbed to 502MB over ~17 hours before OOM kill at 512MB limit
- After auto-restart: dropped to 165MB baseline, then back to ~384MB after Sheets load
- Existing mitigations: `gc.collect()`, 10MB response cap, `max_workers=2`, task mutex
- Conclusion: free tier 512MB is tight; service auto-recovers; no data loss (Sheets persistence)
- Options: accept ~daily crashes, add proactive memory watchdog restart, or upgrade to Starter plan ($7/mo)

## Recently Completed (Session Jan 19, 2026)
- Audio Conversion Status Fix:
  - PROBLEM: Scheduler task completion messages were overwriting audio conversion progress
  - FIX 1: Added `_long_operation_in_progress` flag to track when audio conversion is running
  - FIX 2: Updated `_on_scheduler_task_complete()` to skip status updates when flag is set
  - FIX 3: Audio conversion sets flag at start, clears in finally block
  - Result: Audio conversion progress now shows correctly without scheduler interference

- Audio Output File Detection Fix:
  - PROBLEM: Log showed "Output file exists: False" even when MP3 was successfully created
  - ROOT CAUSE: Code checked for .wav file, but script converts to .mp3 and deletes .wav
  - FIX: Updated file existence check to also look for .mp3 version
  - Also fixed timeout handling to check for MP3 files

- Background Scheduler Daemon (Complete):
  - NEW FILE: scheduler_daemon.py - Standalone background process for scheduled tasks
    - Runs independently of the GUI application
    - Cross-platform support: macOS (LaunchAgent), Windows (Registry), Linux (autostart)
    - CLI interface: start, stop, status, run (foreground)
    - PID file management for daemon state tracking
    - Proper signal handling for graceful shutdown
    - Logging to Application Support folder
  - GUI Integration (gui_app.py):
    - "Background Mode" section in Scheduler area
    - "Enable Background" toggle switch to start/stop daemon
    - Status indicator (Running/Not running)
    - "Start on login" checkbox for persistence across reboots
    - New methods: `_init_background_scheduler_state()`, `_toggle_background_scheduler()`, `_toggle_launch_on_login()`
  - API Functions for GUI:
    - `start_background_scheduler()` - Spawn daemon process
    - `stop_background_scheduler()` - Send SIGTERM to daemon
    - `is_background_scheduler_running()` - Check PID file
    - `enable_launch_on_login()` / `disable_launch_on_login()` - OS-specific autostart
  - Bug fix: URL normalization in scheduler.py (add https:// if missing)

## Recently Completed (Session Jan 18, 2026 - Part 3)
- CSV Header Management (Complete):
  - Added `include_headers` parameter to `export_items_to_sheet()` in sheets_manager.py
  - Scheduler task editor has "Include headers" checkbox - uncheck for append-only mode
  - Config Manager now has "CSV Columns" field to pre-define column headers
  - New configs default to: title, url, date_published
  - Updated _template.json with csv_columns documentation
  - Flow: Define columns in config → Create scheduler task → Uncheck "Include headers" for appending

- Scheduler System (Complete):
  - NEW FILE: scheduler.py - Full backend for automated extraction tasks
    - ScheduledTask dataclass with serialization to/from JSON
    - Scheduler class with background thread (checks every 30 seconds)
    - Intervals: hourly, every_6_hours, every_12_hours, daily, weekly, custom_hours
    - Auto-export to Google Sheets using sheets_manager.py
    - Task persistence to scheduled_tasks.json
  - GUI Integration (gui_app.py):
    - Collapsible Scheduler section in Advanced area (row 2 after Transcription)
    - On/off toggle switch with status indicator (Running/Stopped)
    - Scrollable task list with enable/disable, run now, edit, delete buttons
    - Task editor dialog: name, source URL, config, schedule, Sheets export options
    - Setup Guide popup with comprehensive layman-friendly instructions
  - Setup Guide covers:
    - Quick Start steps (add task, set source, choose config, schedule, enable)
    - Supported sources: Telegram channels, newsletter archives, RSS feeds
    - Google Sheets setup: Cloud Console, Service Account, JSON key, share sheet
    - Tips and troubleshooting

## Recently Completed (Session Jan 18, 2026 - Part 2)
- Calendar Popup Modal Fix:
  - PROBLEM: When calendar popup was open over textbox, mouse events passed through to textbox
  - This caused accidental text selection/modification while picking dates
  - FIX: Added `dlg.grab_set()` to `_open_calendar_for()` to make calendar modal
  - Modal dialogs capture all mouse events, preventing underlying widget interactions
- Newsletter Extraction Quality Fix:
  - PROBLEM: Output had massive duplication - each headline appeared 3-4 times
  - ROOT CAUSE: `_extract_newsletter_content()` iterated over ALL HTML elements (h1-h4, p, li, div)
    and created FetchedItems for each, but same text exists in nested elements
  - ALSO: Navigation/promotional text was leaking through ("Exec Sum, Identifier", "Merch Store", ads)
  - FIX 1: Rewrote `_extract_newsletter_content()` with proper deduplication:
    - Added `seen_headlines` set to track already-processed text
    - Normalizes text (lowercase, whitespace) before dedup check
    - Also checks for substring matches (headline A contained in headline B)
    - Only iterates over h2, h3, p elements (not li, div, h1, h4)
    - Properly tracks excluded sections (Prediction Markets, Meme Cleanser, etc.)
  - FIX 2: Expanded `_is_navigation_text()` to catch promotional content:
    - Added promo phrases: "message from", "use code", "daily newsletter", etc.
    - Added ExecSum-specific ad text patterns
  - FIX 3: Updated `format_items_for_audio()` newsletter section:
    - Changed header to "From {source_name} Newsletter:"
    - Headlines output as clean text without redundant "From X," prefix
  - Result: Clean output matching Data Extractor quality

## Recently Completed (Session Jan 18, 2026)
- Complete Audio Output Overhaul:
  - Rewrote `format_items_for_audio()` for proper TTS-friendly output
  - Added `_clean_title_for_audio()` to remove symbols (|, :, emojis, !!, ??)
  - Section headers now spoken naturally: "From YouTube videos:" not "=== YouTube ==="
  - Video intros: "Regarding the video titled X, published Y" instead of "X (Y):"
  - Article sources: URL domains converted to readable names (execsum.co → "Exec Sum")
- Audio Formatting Prompts Strengthened (v3):
  - Added explicit "START DIRECTLY WITH CONTENT" rule
  - NO preambles like "Here's a summary..." or meta-commentary about the format
  - Explicit examples: NO asterisks, NO **bold**, NO (Transition)/(Intro) labels
  - Numbers/dates examples: "$103,000" → "one hundred three thousand dollars"
- Date Range Filtering Bug Fix:
  - CRITICAL BUG: End date was never being used - only start date filtered videos
  - When user specified Jan 17-17, Jan 18 videos were still included
  - Added `end_date` parameter to `fetch_all_sources()`, `_fetch_youtube()`, `_fetch_rss()`
  - Now properly filters: `start_date <= pub_date <= end_date`
- Smooth Textbox Scrolling:
  - Replaced integer-based `yview_scroll()` with fractional `yview_moveto()` for smoother feel
  - Reduced scroll sensitivity for macOS trackpads
- Newsletter Source Type Integration (COMPLETE):
  - Added `SourceType.NEWSLETTER` to the enum - newsletters now properly recognized
  - Added `config` field to `SourceConfig` to store extraction config name (e.g., "execsum")
  - Created `_fetch_newsletter()` method that uses `DataCSVProcessor` with extraction configs
  - Newsletter items are filtered by include/exclude patterns from extraction config
  - NO Gemini summarization for newsletters - uses extraction config filtering instead
  - Added newsletter handling in `format_items_for_audio()` for TTS output
- Sources Editor Type/Config Dropdowns (COMPLETE):
  - Replaced static badge with Type dropdown: YouTube/Newsletter/RSS/Archive
  - Added Config dropdown that appears when Newsletter type is selected
  - Config dropdown populated from extraction_instructions/*.json files
  - Users can now properly create newsletter sources with type and config
  - Save function uses dropdown values instead of auto-inference
- Newsletter Listing Page Support (FULLY REWRITTEN):
  - PROBLEM: `/authors/` pages were extracting garbage nav links ("Identifier", "404", "Merch Store")
  - ROOT CAUSE: `DataCSVProcessor.process_url()` extracts ALL links from a page for CSV export,
    but `GenericWebExtractor` doesn't apply config filters - only `BeehiivExtractor` does
  - SOLUTION: Completely rewrote newsletter extraction to NOT use DataCSVProcessor
  - NEW APPROACH: `_extract_newsletter_content()` extracts actual TEXT content from posts
    - Parses HTML structure (h1-h4 for sections, p/li/div for content)
    - Applies include/exclude patterns from extraction config directly
    - Skips excluded sections (like "Prediction Markets", "Meme Cleanser")
    - Filters out navigation text with `_is_navigation_text()`
    - Filters out internal links with `_is_internal_link()`
    - Creates TTS-friendly FetchedItems with proper summaries
  - `_fetch_newsletter()` still detects listing vs direct post URLs
  - `_extract_newsletter_post_links()` still extracts `/p/` post links from listing pages
  - Removed unused `_convert_extracted_to_fetched()` method
  - BUG FIX: Added missing `_get_headers()` method to SourceFetcher class
    - Error was: "'SourceFetcher' object has no attribute '_get_headers'"
    - Method returns standard browser-like HTTP headers for web requests

## Recently Completed (Session Jan 17-18, 2026)
- UI Reorganization:
  - Changed header from "Daily News Summary & YouTube Integration" to "Summarize Text, Articles, and Videos"
  - Added separator with "Convert Text/Summaries to Audio" header above audio controls
  - Moved Data Extractor into Advanced section as nested dropdown
  - Added separate Transcription nested dropdown in Advanced
  - Moved Status/Compression section to bottom of window
  - Moved Tutorial button from status bar into Settings dialog
- Config-Based URL Detection in Audio Content:
  - URLs pasted in textbox are checked against extraction config domains
  - ExecSum URLs (execsum.co) show blue banner with "Extract Data" option
  - Extract Data button uses Data Extractor logic instead of AI summarization
  - Formatted results inserted into textbox for audio conversion
- Scroll capture for textbox (scrolling over textbox scrolls textbox, not main window)
- Visual grip icon on textbox resize handle
- Article content cleaning via Gemini AI (same as YouTube transcript cleaning)
- Text scaling slider in Settings (50-150%)
- Bug Fixes (Jan 18, 2026):
  - Fixed textbox scroll capture with enter/leave event handlers to disable parent scroll
  - URL detection banner now always visible with explainer text when inactive
  - Added source_url_patterns field to Config Manager UI (replaces hardcoded domain mapping)
  - Fixed Extract Data button: added ExtractionConfig.from_dict() method, fixed method call to process_url()
  - Updated _format_extraction_results to handle ExtractedItem dataclass objects

## Previous Session Completed
- Source type routing (sources.json v2.0 schema with type/config fields)
- Config Manager window (create, edit, duplicate, delete extraction configs)
- Capabilities field for power-user features (csv_export, grid_enrichment, research_articles, custom_prompts)
- Textbox resize handle for user-adjustable height
- URL detection banner always visible (greyed when inactive)
- Placeholder overlap fix with proper state tracking

## Older Completed (for reference)
- Custom Instructions profile management (New, Duplicate, Rename, Delete, Set Active)
- ExecSum extraction config created (extraction_instructions/execsum.json)
- ExecSum extractor script for training data (execsum_extractor.py)
- ExecSum processor for podcast-style output (execsum_processor.py)
- Training CSV generated: execsum_training_dec24.csv (37 links, 14 pre-excluded)

## ExecSum System Architecture
- execsum.json: Extraction config with blocked domains, exclude patterns, allowed sources
- execsum_extractor.py: Extracts links from newsletter for training/review
- execsum_processor.py: Processes newsletters, filters content, generates podcast text
- Output: Goes to same Week_N_YYYY folder as YouTube news summaries
- Integration: Shares audio generation pipeline with existing system

## Source Processing Architecture (NEW)
- sources.json: Schema v2.0 with type (youtube|newsletter|rss) and config fields
- source_processor.py: Unified routing - loads sources, detects types, routes to processors
- extraction_instructions/*.json: Per-source config with include/exclude patterns, capabilities
- _template.json: Documented template for creating new extraction configs

## Capabilities System
Configs can enable advanced features via the `capabilities` field:
- csv_export: CSV output with custom columns
- grid_enrichment: Grid/database integration
- research_articles: Deep article fetching
- custom_prompts: Custom AI extraction prompts

Consumer builds ship with capabilities disabled by default.
Power users enable as needed for their workflows.

## Config-Based URL Detection (NEW)
The Audio Content section now intelligently detects URLs matching extraction configs:

**How It Works:**
1. When URLs are pasted in the textbox, `_categorize_urls_by_config()` checks article URLs
2. URLs are matched against configs via `source_url_patterns` field or inferred domain mapping
3. If matches found, banner turns blue with "Extract Data" button alongside "Fetch Content"
4. "Extract Data" uses Data Extractor logic (filtering, patterns) instead of AI summarization

**Domain Mapping (in gui_app.py `_load_extraction_configs()`):**
- execsum.co → execsum.json
- cryptosum.beehiiv.com → cryptosum.json
- rwaxyz.com → rwa.json

**To Add New Mappings:**
1. Add `source_url_patterns: ["domain1.com", "domain2.com"]` to your config JSON
2. Or update the `domain_map` dict in `_load_extraction_configs()`

**Key Methods:**
- `_load_extraction_configs()` - Loads configs with source domain info
- `_match_url_to_config()` - Matches a URL to a config
- `_categorize_urls_by_config()` - Separates config-matched vs regular URLs
- `_set_url_banner_active_with_config()` - Blue banner with Extract Data button
- `_extract_config_urls()` - Processes URLs using Data Extractor
- `_format_extraction_results()` - Formats items as readable text

## Key Architecture Decisions
1. When running as frozen PyInstaller app:
   - Config files (channels.txt, sources.json) are READ from bundle (sys._MEIPASS), WRITTEN to data dir
   - Output files (Week folders, summaries, audio) go to ~/Library/Application Support/Daily Audio Briefing/
   - Scripts run IN-PROCESS via import, not subprocess

2. When running in development mode:
   - All files read/write from script directory (os.path.dirname(__file__))
   - Scripts run via subprocess

## Files Modified for Frozen App Support
- audio_generator.py - runs scripts in-process when frozen, uses Application Support for base_dir
- get_youtube_news.py - added get_data_directory() and get_resource_path()
- make_audio_quality.py - added get_resource_path() for bundled model files
- gui_app.py - added get_data_directory() and get_resource_path() helpers; instruction profile management
- DailyAudioBriefing.spec - scripts as hiddenimports instead of data files
- instruction_profiles.json - stores multiple named custom instruction profiles

## Known Issues to Fix
- [x] "Convert Selected Dates to Audio" can't find Week folders (uses wrong path when frozen) - FIXED
- [x] Any other gui_app.py functions using os.path.dirname(__file__) for Week folder access - FIXED
- [x] Audio conversion in frozen mode: no stdout/stderr capture, no cwd change - FIXED
- [x] kokoro_onnx config.json not bundled - FIXED
- [x] language_tags/phonemizer/segments/csvw data files not bundled - FIXED
- [x] espeakng_loader/espeak-ng-data not bundled - FIXED

## Fixed Functions (now use get_data_directory()):
- upload_text_file() - file dialog initial directory
- select_dates_to_audio() - finds Week folders, archive folder
- view_archive() - finds Archive folder, restores to data directory
- convert_summaries_to_audio() - output path, opens folder after conversion
- All nested functions within these (archive cleanup, unarchive, etc.)

---

# Session — 2026-02-21: Backfill, Tooltips, Guide Update

## Features Added

### Backfill System (⏪ button)
- **Archive crawler**: `BeehiivExtractor.get_archive_posts()` crawls paginated archive pages (`?page=0`, `?page=1`, etc.), extracts post URLs with dates from `<time>` tags, rate-limited at 0.5s between pages
- **Slug-based dedup in crawler**: Same URL appears twice per page (title link + read more link). Fixed by deduplicating on `/p/slug` portion via regex instead of full URL
- **Gap-aware backfill**: `Scheduler.backfill_task()` reads ALL dates already in the sheet via `get_covered_dates_in_sheet()`, fetches archive from earliest date, filters to only posts whose dates aren't already covered. This fills gaps anywhere in the date range, not just after the last entry.
- **Stoppable**: Red "Stop" button appears during backfill, sets `_backfill_stop` flag checked between posts
- **Chunked**: Processes one post at a time with 1s pauses, GC every 5 posts

### Copy Button on Task Log
- Copy button in log header copies full log to clipboard
- Shows "Copied!" feedback for 1.5s

### Tooltips
- Added scheduler-specific tooltips: Add Task, scheduler mode, log toggle/copy/clear/stop
- Added tooltips on dynamic task row buttons: ▶ Run, ⏪ Backfill, ✎ Edit, ✕ Delete

### Guide Page Updated
- Documented all task row buttons (▶, ⏪, ✎, ✕)
- Backfill section: how it works, gap detection, dedup, chunked processing, Stop button
- Advanced Capabilities section: Grid enrichment, Research articles, capability badges
- Task Log section: toggle, copy, clear, stop
- Scheduler modes: Local vs Cloud
- New troubleshooting entries: 0 rows (dedup), backfill 0 posts
- Sheet notes: columns W (Feedback for Bots) and X (SKIP)

## Key Files Modified
- `gui_app.py` — Copy button, ⏪ button, Stop button, backfill logic, tooltips, guide text
- `data_csv_processor.py` — `get_archive_posts()`, slug-based dedup
- `sheets_manager.py` — `get_last_date_in_sheet()`, `get_covered_dates_in_sheet()`, optimized `get_existing_urls()`
- `scheduler.py` — `backfill_task()` with gap-aware logic, stop flag support
- `scheduled_tasks.json` — Re-added `enrich_with_grid` and `research_articles` flags

## Problem/Solution
- **0 rows to Sheets after task run**: Deduplication working correctly — all 43 items from Feb 20 CryptoSum already existed in the sheet from previous test runs
- **Archive crawler duplicates**: Same post URL appeared 2x per page. Fixed with slug-based dedup via `re.search(r'/p/([^/?#]+)', post_url)`
- **Backfill missed gaps**: Initial version only checked last date. Sheet had data on Dec 30-31, Jan 5-6, Feb 20 with a 45-day gap. Fixed by getting ALL covered dates and filtering archive posts against the full set
- **Grid+Research flags keep dropping**: Old app (without these fields in ScheduledTask model) overwrites JSON on save. Re-added after each build.

---

# Session — 2026-02-21 (evening): Sheet Cleanup, Re-enrich, Re-title

## Summary
Massive CryptoSum sheet cleanup session + RWA title truncation fix. Added several new scheduler capabilities for maintaining sheet data quality.

## Changes

### CryptoSum Sheet Cleanup
- **Removed title column** — Contained only useless 2-3 letter source abbreviations (TB, DC, CT). Used Sheets API `deleteDimension` to delete it, then `moveDimension` to move `url` to column A. Config already had `csv_columns` starting with `url`.
- **SKIP marking** — Analyzed 29 existing SKIP=TRUE rows, then marked 555 additional rows as SKIP=TRUE with reasoning in "Feedback for Bots" column. Criteria: "Headline Roundup" items with no Grid entity match = general news, skip. Sponsored/ad content = skip. Launches/VC/M&A = keep.
- **Date sorting** — Added `sort_sheet_by_date()` to sheets_manager.py using Sheets API `sortRange` for server-side sorting. Integrated into both `_execute_task` and `backfill_task` pipelines.
- **Dedup enhancement** — Consolidated duplicate `deduplicate_sheet()` functions (new batch-delete at line 410 shadowed existing clear+rewrite at line 633). Enhanced the clear+rewrite version to also remove empty rows.
- **RWA dedup** — Cleaned RWA sheet from 10,142 → 842 rows (9,300 duplicates removed).

### Grid Re-enrichment System
- **`reenrich_task()`** in scheduler.py — Reads existing sheet rows, identifies those missing `grid_matched` data, creates ExtractedItem objects, runs Grid entity matching in batches of 50, writes grid columns back via Sheets API batchUpdate.
- **🔄 Re-enrich button** (purple) — Shown on tasks with `enrich_with_grid` enabled.
- **Result**: 150 rows processed, 112 matched to Grid entities.
- **Bug fix**: Initial import used `DataProcessor` (doesn't exist) instead of `DataCSVProcessor`. Also needed `ExtractionConfig` import and correct constructor args.

### Flag Persistence Fix
- **Root cause**: `enrich_with_grid` and `research_articles` flags kept being dropped because the Application Support runtime copy of `scheduled_tasks.json` didn't have them — defaulted to `false` on load, then overwrote the file on save.
- **Fix**: Explicitly added flags to BOTH the project dir and Application Support copies. The ScheduledTask model already handled serialization correctly (lines 84-85, 110-111).

### Telegram Title Truncation Fix
- **Root cause**: `TelegramExtractor.extract()` had `title = message_text[:100]` with `...` appended. 841/842 RWA rows were truncated.
- **Fix**: Removed the 100-char cap, title now uses full `message_text`.
- **`retitle_task()`** in scheduler.py — Paginates through ALL historical Telegram messages (manual page-by-page with `?before=` param), builds URL→full_title map, batch-updates truncated titles in sheet.
- **✏️ Re-title button** (orange) — Shown on Telegram-sourced tasks.
- **Stop fix**: Initial version used single blocking `process_url()` call with no stop checks. Replaced with manual pagination loop that checks `stop_flag` between pages. 50-page safety cap.

### New sheets_manager Utilities
- `delete_column()` — Deletes a column by header name using Sheets API `deleteDimension`
- `sort_sheet_by_date()` — Sorts all data rows by a date column using Sheets API `sortRange`
- Auto-dedup + sort integrated into `_execute_task` and `backfill_task`

## Key Files Modified
- `data_csv_processor.py` — Removed TelegramExtractor title truncation, archive URL fix (`/archive?page=N`), duplicate page logic
- `sheets_manager.py` — `delete_column()`, `sort_sheet_by_date()`, enhanced `deduplicate_sheet()`, removed duplicate function
- `scheduler.py` — `reenrich_task()`, `retitle_task()` with manual pagination, auto-dedup/sort in pipelines, import fixes
- `gui_app.py` — 📊 Sheet button, 🔄 Re-enrich button, ✏️ Re-title button, `_reenrich_task()`, `_retitle_task()`, Guide updates

## Problem/Solution
- **702 empty rows in CryptoSum**: Deleted by enhanced `deduplicate_sheet()` which now removes empty rows (only FALSE/blank cells)
- **Archive crawler only finding 12 posts**: Used homepage `/?page=N` instead of `/archive?page=N`. Beehiiv homepage only shows recent posts.
- **Archive crawler stopping after page 1**: Pages 0 and 1 return identical content. After page 0, all page 1 slugs already seen → `page_posts` empty → break. Fixed by tracking `raw_link_count`.
- **Duplicate `deduplicate_sheet()` functions**: Python loads last definition, so old clear+rewrite version ran. New batch-delete version at line 410 was never called. Removed the new one, enhanced the old one.
- **Re-enrich import crash**: `DataProcessor` doesn't exist — it's `DataCSVProcessor`. Constructor takes `ExtractionConfig()`, not `config_name` string.
- **Re-title unstoppable**: Single `process_url()` call paginated internally with no stop checks. Replaced with manual page loop.
- **Global task mutex**: `_task_running` boolean prevents running re-enrich + re-title simultaneously even on different tasks/sheets. Noted for fix.

---

# Session: Feb 23, 2026 — API Cost Protection + Briefing Pipeline

## API Cost Protection (Critical priority)

### Problem
Zero API usage tracking or cost protection. Scheduler could make 100+ Gemini API calls/day with no visibility or limits.

### Solution — `api_usage_tracker.py` (new, ~310 lines)
Thread-safe singleton tracker wrapping every `model.generate_content()` call:
- `tracked_generate(model, prompt, caller)` — pre-flight limit check → API call → record
- `APILimitExceeded` exception raised when daily/monthly caps hit
- Thread-local task context (`set_current_task`/`clear_current_task`) for per-scheduler-task attribution
- JSON persistence with lazy day/month rollover, atomic `os.replace()` writes
- Cost estimation: `chars / 4 ≈ tokens` × model pricing table

### Instrumented 7 call sites across 4 files
- `gui_app.py`: 3 sites (_clean_article_content, _summarize_youtube_transcript, _process_audio_content)
- `source_fetcher.py`: 2 sites (_summarize_youtube, _summarize_article)
- `get_youtube_news.py`: 1 site (summarize_text)
- `grid_api.py`: 1 site (analyze_profile_with_ai)

### Scheduler task context (scheduler.py)
Added `set_current_task`/`clear_current_task` in 4 methods: `_execute_task`, `_run_backfill`, `_run_reenrich`, `_run_retitle`

### Settings UI (gui_app.py)
New "API Usage & Limits" card on Settings page with daily/monthly progress bars, cost estimates, enable/disable switch, limit config, per-task breakdown

### Web dashboard (web_app.py + templates/index.html)
4 new API endpoints: GET /api/usage/stats, GET /api/usage/history, GET /api/usage/tasks, GET/PUT /api/usage/limits. Usage stats panel in web Settings.

---

## Briefing Pipeline (High Priority — New Feature)

### Problem
App's core value proposition (audio briefing) required manual 3-step workflow: Summarize → Audio → Drive. Could not be automated via scheduler.

### Solution — New `briefing_pipeline` task type

**ScheduledTask dataclass** — 6 new fields: `task_type`, `audio_quality`, `audio_voice`, `upload_to_drive`, `drive_folder_id`, `source_filter`

**`_execute_pipeline_task()` in scheduler.py** (~130 lines) — 6-step chain:
1. Load + filter sources from `sources.json`
2. `SourceFetcher.fetch_all_sources()` → AI-summarize
3. `format_items_for_audio()` → TTS-ready text
4. Save summary to `Week_N_YYYY` folder
5. Generate audio via `make_audio_quality.py` / `make_audio_fast.py` subprocess (skipped in server mode)
6. Upload audio to Google Drive via `drive_manager.upload_file()` (if configured)

**Desktop task editor** — CTkSegmentedButton type selector ("Data Extraction" / "Audio Briefing") with conditional field visibility. Pipeline fields: audio quality radio, Kokoro voice selector, source filter checkboxes, Drive upload + folder ID.

**Web task editor** — Same type toggle, pipeline fields, [Pipeline] badge on task cards.

### Key Design Decisions
- Source selection: defaults to ALL enabled sources, optional per-task filter
- Audio: direct subprocess.run() to TTS scripts (no GUI dependency)
- Server mode: gracefully skips audio + Drive, saves summary text only
- API key: `FileManager.load_api_key()` from `.env`, fallback to env var

## Key Files Modified
- `api_usage_tracker.py` — NEW: Thread-safe API usage tracker singleton
- `scheduler.py` — Extended ScheduledTask (6 fields), `_execute_pipeline_task()`, task type routing, task context
- `gui_app.py` — 3 API call sites wrapped, Settings UI card, extended task editor with type toggle + pipeline fields
- `source_fetcher.py` — 2 API call sites wrapped
- `get_youtube_news.py` — 1 API call site wrapped
- `grid_api.py` — 1 API call site wrapped
- `web_app.py` — 4 usage API endpoints, pipeline fields in task create endpoint
- `templates/index.html` — Usage stats panel, task type toggle, pipeline fields, [Pipeline] badge
- `CLAUDE.md` — Updated pending work, key files table

## Do NOT
- Break the working development mode (Launch Audio Briefing.command)
- Change the output folder structure (Week_N_YYYY format)
- Remove any existing functionality
