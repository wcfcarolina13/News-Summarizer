> **Note:** This file is no longer actively maintained. See `CLAUDE.md` at the project root for current project state and TODOs.

# Development Progress

Last updated: 2026-01-17

## Recently Completed (Jan 17, 2026)

### MAJOR: Get Summaries Multi-Source Support (Phase 2 Complete)
- **Renamed "Get YouTube News" to "Get Summaries"** - now supports multiple source types
- **New `source_fetcher.py` module** - unified content fetching for:
  - **YouTube Channels** - fetches transcripts via scrapetube + yt_dlp, summarizes with AI
  - **RSS Feeds** - parses Atom/RSS feeds from any URL
  - **Article Archives** - extracts links from author/archive pages like execsum.co
- **Article archive selector dialog** - when processing archive pages:
  - Extracts all article links from the page
  - Shows dialog letting user select which articles to fetch
  - Pre-selects articles within date range, shows others in orange
  - Selection count, Select All/None/In Range buttons
- **Updated sources editor with type badges**:
  - **YT** (red) = YouTube channel
  - **RSS** (orange) = RSS/Atom feed
  - **ARC** (blue) = Article archive page
  - Badges update automatically as you edit URLs
  - Source type saved to sources.json
- **Type inference from URL patterns**:
  - youtube.com, youtu.be → YouTube
  - .rss, .xml, /feed, /rss → RSS
  - Everything else → Article Archive
- **Backward compatibility**:
  - Legacy `channels.txt` still works
  - Legacy `sources.json` without type field auto-infers types
  - `get_youtube_news_from_channels()` redirects to new `get_summaries_from_sources()`
- **Optional dependencies with fallbacks**:
  - dateparser → fallback to manual date parsing
  - requests, beautifulsoup4 → graceful failure messages

### MAJOR: Unified Content Editor (Phase 1 Complete)
- **Eliminated popup-based "Direct Audio" flow** - replaced with inline editor
- **New inline status bar** below textbox showing cleaning status
- **Toggle button** switches between raw and cleaned text views
- **Yellow URL detection banner** appears when URLs are pasted
  - "Fetch Content" button to pull in articles/videos
  - "Keep as Text" to ignore URLs
- **Auto-clean on Generate** - text is automatically cleaned when Generate is clicked
- **Removed Direct Audio checkbox** - no longer needed, workflow is unified
- **Updated tutorials** to reflect new inline workflow
- **Cache preserved** for instant regeneration
- **Section renamed**: "News Summary" → "Audio Content"

### UI Consolidation: Advanced Section for Transcription
- **Transcription features moved to collapsible "Advanced" section**
  - Transcription is a niche feature requiring extra API fees or large local tools (faster-whisper)
  - New collapsible "Advanced" section at bottom of app (collapsed by default)
  - Contains: Upload Audio/Video button, file selector, Transcribe button, status indicator
- **Upload Text File button simplified**
  - Renamed to "Upload Text File (.txt)" - now only handles text files
  - Loads file content directly into News Summary textbox (no more combo/transcribe flow)
  - Audio file upload moved to Advanced section
- **Cleaner main UI**: Removes clutter for users who don't need transcription

### UI Improvements: Toggle Raw/Cleaned & Cache Fix
- **"Use Raw Text" button is now a toggle**
  - Previously: Clicking "Use Raw Text" permanently replaced cleaned text with raw
  - Now: Button toggles between "Use Raw Text" / "Use Cleaned" allowing users to switch views
  - Cleaned text is preserved when toggling, so users can compare or switch back
  - Toggle state tracked via `showing_raw` and `saved_cleaned_text` variables
- **Cache check now happens BEFORE URL confirmation dialog**
  - Previously: URLs Detected dialog appeared every time, causing re-processing even when cache existed
  - Now: `show_direct_audio_dialog()` checks cache first - if valid cache exists, skips URL confirmation
  - Flow: cache check → cache hit? → direct to preview; cache miss with URLs? → show URL confirmation
  - This prevents unnecessary re-cleaning when opening the preview dialog multiple times

### Bug Fixes: URL Processing & Cache Preservation
- **URLs now detected even when Direct Audio is unchecked**
  - Previously: URLs in text were passed as literal text to audio generator (not fetched)
  - Now: Shows confirmation dialog asking to fetch URLs or generate as-is
  - New method: `_show_url_processing_for_non_direct()` - handles URL detection without Direct Audio
- **Cache preserved when embedded URL confirmation appears**
  - Previously: Clicking "Text Only" in URL confirmation dialog cleared the cache
  - Now: Original raw_text hash preserved, cache works correctly across dialog flow

### Article Custom Instructions
- **Custom Instructions now support both YouTube AND Article processing**
- **Tabbed interface**: Custom Instructions editor now has two tabs:
  - 📺 **YouTube** - Instructions for video transcript summarization
  - 📄 **Articles** - Instructions for article cleaning and processing
- **Separate templates**: Each tab has its own default template with relevant examples
- **Profile system extended**: Each profile now stores both `instructions` (YouTube) and `article_instructions`
- **Migration support**: Existing profiles automatically get the article instructions template added
- **Clear/Reset buttons**: Work on the currently selected tab (YouTube or Article)
- **New helper functions**:
  - `_get_active_article_instructions()` - Retrieves article instructions from active profile
  - `_get_active_youtube_instructions()` - Retrieves YouTube instructions from active profile
- **Updated methods**:
  - `_clean_single_article()` - Now incorporates custom article instructions into the AI prompt
  - `_summarize_youtube_transcript()` - Now incorporates custom YouTube instructions into the AI prompt

### Universal Input: Smart URL Detection
- **News Summary textbox now handles everything** - YouTube URLs, article URLs, and plain text
- **Smart content detection**: Auto-detects URL types (YouTube vs article) and processes appropriately
- **Embedded URL confirmation**: When URLs are found in pasted text, asks user if they want to fetch them
- **Consolidated workflow**: Removed separate "Specific URLs" button - all URL processing now in one place
- **New helper functions**:
  - `_detect_content_type()` - Analyzes text for YouTube URLs, article URLs, plain text
  - `_fetch_youtube_transcript()` - Fetches video transcript and metadata
  - `_process_mixed_content()` - Handles mixed YouTube + article + text processing
  - `_summarize_youtube_transcript()` - AI summarization of video content
- **Output organized by source and date** - Each item clearly labeled with source and timestamp

### Bug Fix: Direct Audio / gTTS Not Producing Audio
- **Root Cause**: Directory mismatch between `FileManager` and `AudioGenerator` when running as frozen app
  - `FileManager.base_dir` pointed to app bundle (read-only)
  - `AudioGenerator.base_dir` pointed to Application Support (writable)
  - `save_summary()` saved `summary.txt` to wrong location, so `make_audio_fast.py` couldn't find it
- **Fix**: Updated `file_manager.py` to use Application Support directory when running as frozen app
  - Now matches `AudioGenerator`'s behavior
  - Both components use the same writable directory

### API Key Persistence Across Reinstalls
- **API keys now persist across app reinstalls** (stored in Application Support, not app bundle)
- **One-time migration**: If API key exists in old bundled location, it's automatically migrated
- **Security**: `.env` file is in `.gitignore` - API keys are NEVER pushed to GitHub

### Direct Audio Text Cache
- **Cleaned text is now cached** - if you accidentally close the dialog, re-opening it loads the cached version instantly
- **"Re-clean" button** - manually re-run AI cleaning on the current News Summary textbox content
- **Cache persists edits** - even if you cancel, your edits are saved to the cache
- **Smart cache invalidation** - cache only used if the raw text hash matches (change the source text = fresh clean)

### UI/UX Improvements
- **gTTS Sample Button**: Added "▶ Sample" button next to "Generate Fast (gTTS)" so users can hear what gTTS sounds like before generating
- **Grid/Research Checkboxes**: Now disabled when ExecSum config is selected (with tooltip explaining why)
- **Mode Toggle Clarity**: Made URL/HTML mode tabs more visually clear with filled/empty bullets (● vs ○) and borders
- **Model Dropdown**: Shows actual model names (gemini-2.0-flash, etc.) instead of just labels

### Edit Sources Window
- **Export CSV Button**: New button to export news sources as CSV backup file
  - Saves URL and enabled status for each source
  - Users can restore by using Bulk Import

### Custom Instructions Persistence Fix
- **Profiles now persist across app reinstalls**
  - Moved `instruction_profiles.json` to persistent data directory:
    - macOS: `~/Library/Application Support/Daily Audio Briefing/`
    - Windows: `%APPDATA%/Daily Audio Briefing/`
  - One-time migration from old bundled location
- **Default template now visible**: New installs see a helpful template with examples instead of blank
- **Reset to Template button**: Easily reset instructions to the default template
- **Updated `get_youtube_news.py`** to also check data directory for custom_instructions.txt

### ExecSum Newsletter Processor
- Created `execsum_processor.py` for processing ExecSum finance newsletters
- Trained extraction config (`execsum.json`) with 100% accuracy on Dec 24 and Dec 29 newsletters
- Features:
  - Extracts Markets and Headline Roundup sections
  - Multi-URL batch processing with date-based sorting
  - Programmatic text cleanup (replaced AI summarization to avoid item dropping)
  - TTS-friendly output (expands abbreviations like bps→basis points)
  - Handles `<br>` tag parsing properly

### GUI Improvements
- Added ToolTip class with 1.2 second hover delay
- Added multi-line text area for entering multiple URLs (one per line)
- Added tooltips to all buttons explaining their function
- Updated extraction logic to process multiple URLs sequentially

### Documentation
- Added Command Line Guide section to README.md
- Documents execsum_processor.py, get_youtube_news.py, and audio generation scripts

## Pending Tasks

### High Priority
1. **Rebuild the macOS app** to include the new changes
   ```bash
   cd daily_audio_briefing
   python3 build_app.py  # Use python3 on macOS
   ```
   Then close existing app and copy from dist/ to /Applications/

2. **Test the new multi-URL feature** in the GUI

### Future Improvements
- Consider adding progress indicator for multi-URL extraction
- Add ability to save/load URL lists for recurring newsletter batches
- Add keyboard shortcuts for common actions

## Key Files Modified
- `gui_app.py` - Unified Content Editor, Get Summaries multi-source, article selector dialog, type badges in sources editor
- `source_fetcher.py` - NEW: Unified source fetching module (YouTube, RSS, Article Archives)
- `audio_generator.py` - Added `play_gtts_sample()` method
- `file_manager.py` - Fixed to use Application Support directory when running as frozen app (matching AudioGenerator)
- `get_youtube_news.py` - Updated to check data directory for custom_instructions.txt
- `execsum_processor.py` - Main newsletter processor
- `extraction_instructions/execsum.json` - Trained config for ExecSum
- `README.md` - Added CLI guide

## Known Issues
- None currently

## Test Files (can be archived)
Test output files in `Week_3_2026/`:
- `execsum_digest_2026-01-17_*.txt` - Various test outputs from development
- Keep `execsum_digest_2026-01-17_1325.txt` as the latest working output

## Build Instructions

**Note:** On macOS, use `python3` instead of `python`:

```bash
# From daily_audio_briefing directory:
python3 build_app.py

# Then copy to Applications:
# Close the app first if running
rm -rf "/Applications/Daily Audio Briefing.app"
cp -R "dist/Daily Audio Briefing.app" /Applications/
```
