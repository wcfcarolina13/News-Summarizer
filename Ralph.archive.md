# Ralph - Development Rails System
# Purpose: Keep the News Summarizer project focused and trim during development

## Current Focus
- UI Polish: Streamlined layout with clearer section separation
- Audio Content Integration: Seamless flow from text/URL input to audio generation

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

## Do NOT
- Break the working development mode (Launch Audio Briefing.command)
- Change the output folder structure (Week_N_YYYY format)
- Remove any existing functionality
