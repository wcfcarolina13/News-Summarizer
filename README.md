# Daily Audio Briefing

A desktop application for generating daily audio news summaries from YouTube channels, articles, and newsletters using AI summarization.

## Features

### Core Features
- **YouTube News Aggregation**: Fetches and summarizes videos from configured YouTube channels
- **AI-Powered Summarization**: Uses Google Gemini AI to create concise, audio-friendly summaries
- **Multiple Audio Formats**: Generate audio in both fast (gTTS) and high-quality (Kokoro TTS) modes
- **Date Range Processing**: Fetch news from specific date ranges or recent days
- **Voice Selection**: Choose from multiple voice presets for high-quality audio generation

### Direct Audio Mode (NEW)
- **Convert Articles to Audio**: Skip summarization and convert article text directly to audio
- **Fetch Articles from URLs**: Paste one or multiple article URLs to fetch their content
- **Auto-fetch URLs**: Automatically detect and fetch URLs pasted in the text area
- **AI Text Cleaning**: Gemini cleans text for listening (removes URLs, CTAs, formatting, etc.)
- **Smart Filenames**: Audio files named by date and topic (e.g., `2025-12-28_bitcoin-etf-approval.wav`)

### Data Extraction (NEW)
- **Newsletter Extraction**: Extract article links from newsletters (Beehiiv, Substack, etc.)
- **Grid Integration**: Match extracted entities to The Grid database
- **LLM Reasoning**: AI-powered suggestions for Grid profile updates
- **CSV Export**: Export extracted data with Grid matching results

### API Key Management (NEW)
- **Save Button (💾)**: Save API key with visual confirmation (button turns green ✓)
- **Visibility Toggle (👁)**: Show/hide API key in the entry field
- **Key Manager (⚙)**: Popup to view masked key, copy to clipboard, or clear saved key

## Requirements

- Python 3.8+
- Google Gemini API key (free tier available)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone or download this repository

2. Install dependencies:
   ```bash
   cd daily_audio_briefing
   pip install -r requirements.txt
   ```

3. Set up your API key:
   - Launch the app and paste your API key in the "API Key" field
   - Click 💾 to save (button turns green when saved)
   - Get a free API key at: https://aistudio.google.com/apikey

4. Configure your news sources:
   - Click "Edit Sources" to add YouTube channel URLs
   - Or use the "Fetch Article" button to fetch individual articles

## Usage

### Launch the GUI Application

**macOS:**
```bash
./Launch Audio Briefing.command
```

**Windows/Linux:**
```bash
cd daily_audio_briefing
python gui_app.py
```

### API Key Setup

1. **Enter API Key**: Paste your Gemini API key in the top field
2. **Save Key**: Click 💾 (floppy disk) - button flashes green ✓ when saved
3. **Toggle Visibility**: Click 👁 to show/hide the key
4. **Manage Key**: Click ⚙ to open the Key Manager:
   - View masked key
   - Copy key to clipboard
   - Clear saved key

### Workflow 1: YouTube News Summary

1. **Select Model**: Choose from:
   - Fast (FREE): 4000 requests/min
   - Balanced (FREE): 1500 requests/day
   - Best (FREE, 50/day): Highest quality

2. **Fetch News**:
   - Set days to fetch (default: 7 days)
   - Or enable "Use date range" and select specific dates
   - Click "Get YouTube News" to fetch and summarize

3. **Generate Audio**:
   - **Fast**: Click "Generate Fast (gTTS)" for quick text-to-speech
   - **Quality**: Select a voice, preview with "Play Sample", then click "Generate Quality"

### Workflow 2: Direct Audio from Articles (NEW)

Convert articles directly to audio without summarization:

1. **Enable Direct Audio**: Check "Direct Audio (clean text for listening, no summary)"

2. **Add Content** (choose one method):
   - **Paste text**: Paste article content directly into the text area
   - **Paste URLs**: Paste one or more article URLs (one per line)
   - **Fetch Article**: Click "Fetch Article" button and enter URLs

3. **Configure Settings** (optional):
   - Click "Settings" to open app settings
   - Enable "Auto-fetch URLs in Direct Audio mode" to automatically fetch pasted URLs

4. **Generate Audio**:
   - Click "Fast" or "Quality" button
   - Preview dialog shows cleaned text (AI removes URLs, CTAs, formatting)
   - Edit if needed, then click "Convert to Audio"

5. **Smart Filename**: Audio file is automatically named:
   - Single article: `2025-12-28_bitcoin-etf-approval.wav`
   - Multiple articles: `2025-12-28_crypto-markets-regulation.wav`

### Workflow 3: Fetch Multiple Articles

1. **Click "Fetch Article"** button next to the text area
2. **Paste multiple URLs** (one per line):
   ```
   https://example.com/article1
   https://another-site.com/article2
   https://newsletter.substack.com/p/article3
   ```
3. **Click "Fetch All"** - progress shows "Fetching article 1/3..."
4. **Content is combined** with `---` separators between articles
5. **Use Direct Audio** to clean and convert to audio

### Workflow 4: Data Extraction (Advanced)

Extract and enrich article data from newsletters:

1. **Paste newsletter content** or URL in text area
2. **Select extraction config** from dropdown
3. **Enable options**:
   - "Enrich with Grid" - match entities to The Grid database
   - "Research Articles" - fetch article content and run LLM analysis
4. **Click "Extract Links"**
5. **Results** appear in table with Grid matches and suggestions
6. **Export** to CSV with all enrichment data

### Settings

Click "Settings" button to configure:
- **Auto-fetch URLs**: When enabled, URLs pasted in text area are automatically fetched when using Direct Audio mode

### File Organization

- Summaries organized in `Week_*` folders by week number
- Individual daily summaries: `summary_YYYY-MM-DD.txt`
- Audio files: Named by date and topic (e.g., `2025-12-28_topic-name.wav`)
- Check logs in `gui_log.txt` if issues occur

### Command Line Usage

```bash
# Fetch news for the last 7 days
python get_youtube_news.py --days 7

# Fetch news for a specific date range
python get_youtube_news.py --start 2024-12-01 --end 2024-12-07

# Generate fast audio
python make_audio_fast.py

# Generate quality audio with specific voice and filename
python make_audio_quality.py --voice af_sarah --output 2025-12-28_my-topic.wav
```

## Model Options

- `gemini-2.0-flash-exp`: Fastest, 4000 requests/min (default)
- `gemini-1.5-flash`: Balanced, 1500 requests/day
- `gemini-1.5-pro`: Highest quality, 50 requests/day

## Supported Article Sources

Direct Audio mode supports fetching from:
- **Substack** newsletters
- **Beehiiv** newsletters
- **Medium** articles
- **News sites** (CoinDesk, CoinTelegraph, Bloomberg, etc.)
- **Most article-based websites**

## Troubleshooting

- **No summaries generated**: Check that channels.txt has valid YouTube channel URLs
- **API errors**: Verify your API key is correct (click 👁 to check)
- **"API key expired"**: Get a new key at aistudio.google.com
- **No audio output**: Check gui_log.txt for error details
- **Article fetch failed**: Some sites block automated access; try pasting content directly
- **Missing transcripts**: Some YouTube videos may not have captions available

## Debug Output

The app outputs helpful debug messages to the console:

```
[API Key] Saving key: ****abcd
[API Key] Saved successfully
[Fetch] Fetching URL 1/4: https://example.com/article...
[Fetch] Success: 5230 chars
[Audio] Generated filename: 2025-12-28_bitcoin-regulation.wav
[LLM] Analyzing: Coinbase
[LLM] Suggest: DESCRIPTION: Coinbase expands...
```

## Notes

- The AI skips duplicate content and promotional videos automatically
- Summaries are optimized for audio playback (natural speech, no bullet points)
- Direct Audio mode cleans text for listening (removes markdown, URLs, CTAs)
- Generated files are organized weekly for easy management
- **Audio files**: WAV files are large (~100MB+). See [Audio Compression Guide](AUDIO_COMPRESSION_GUIDE.md) for MP3 conversion

## Architecture

The application follows a modular design:

- **gui_app.py**: Main GUI application and event handling
- **file_manager.py**: File I/O operations (summaries, API keys)
- **audio_generator.py**: Audio generation and subprocess management
- **voice_manager.py**: Voice preset management
- **data_csv_processor.py**: Data extraction and Grid enrichment
- **grid_api.py**: The Grid API integration
- **get_youtube_news.py**: YouTube video fetching and AI summarization
- **make_audio_fast.py**: Fast audio generation using gTTS
- **make_audio_quality.py**: High-quality audio generation using Kokoro TTS

## Progress

✅ GUI application with date range controls
✅ Multi-model support (Flash, Pro)
✅ Batch audio conversion
✅ Source management interface
✅ Voice preview system
✅ **Direct Audio mode** - convert articles without summarization
✅ **Multi-URL fetching** - fetch multiple articles at once
✅ **Auto-fetch URLs** - automatic URL detection and fetching
✅ **Smart filenames** - date + topic-based audio naming
✅ **API Key Manager** - save, view, copy, clear keys
✅ **Data Extraction** - newsletter extraction with Grid matching
✅ **LLM Reasoning** - AI suggestions for Grid profiles

Ready for production use!
