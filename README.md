# Daily Audio Briefing

A desktop + web application that creates personalized audio news briefings from YouTube channels, articles, and newsletters using AI summarization and text-to-speech. Includes an automated scheduler that extracts data on a recurring schedule and exports to Google Sheets.

## Download

**[Download the latest release](https://github.com/wcfcarolina13/News-Summarizer/releases/latest)**

| Platform | Download |
|----------|----------|
| **macOS** | `DailyAudioBriefing-X.X.X-macOS.dmg` |
| **Windows** | `DailyAudioBriefing-X.X.X-Windows-Setup.exe` |

### Installation

**macOS:**
1. Download the `.dmg` file
2. Open it and drag "Daily Audio Briefing" to Applications
3. Launch from Applications folder

**Windows:**
1. Download the `-Setup.exe` file
2. Run the installer
3. Launch from Start Menu or Desktop shortcut

### Requirements

- **Google Gemini API key** (free tier available) - [Get one here](https://aistudio.google.com/apikey)
- **FFmpeg** (optional, for audio compression):
  - macOS: `brew install ffmpeg`
  - Windows: `choco install ffmpeg` or [download manually](https://ffmpeg.org/download.html)

---

## Features

### Core Features
- **YouTube News Aggregation**: Fetches and summarizes videos from configured YouTube channels
- **AI-Powered Summarization**: Uses Google Gemini AI to create concise, audio-friendly summaries
- **Multiple Audio Formats**: Generate audio in both fast (gTTS) and high-quality (Kokoro TTS) modes
- **Date Range Processing**: Fetch news from specific date ranges or recent days
- **Voice Selection**: Choose from multiple voice presets for high-quality audio generation

### Direct Audio Mode
- **Convert Articles to Audio**: Skip summarization and convert article text directly to audio
- **Fetch Articles from URLs**: Paste one or multiple article URLs to fetch their content
- **Auto-fetch URLs**: Automatically detect and fetch URLs pasted in the text area
- **AI Text Cleaning**: Gemini cleans text for listening (removes URLs, CTAs, formatting, etc.)
- **Smart Filenames**: Audio files named by date and topic (e.g., `2025-12-28_bitcoin-etf-approval.wav`)

### Data Extraction
- **Newsletter Extraction**: Extract article links from newsletters (Beehiiv, Substack, etc.)
- **Grid Integration**: Match extracted entities to The Grid database
- **LLM Reasoning**: AI-powered suggestions for Grid profile updates
- **CSV Export**: Export extracted data with Grid matching results
- **Google Sheets Export**: Export directly to Google Sheets

### Automated Scheduler
- **Recurring Extraction Tasks**: Schedule data extraction to run hourly, daily, weekly, or on a custom interval
- **Google Sheets Export**: Automatically push extracted data to Google Sheets after each run
- **Task Management**: Enable/disable tasks, edit schedules, run tasks on demand
- **Column Configuration**: Use config defaults or define custom columns for Sheets export
- **Live Preview**: Preview how data will look in your spreadsheet before saving

### Web Dashboard
- **Mobile-Friendly Interface**: Full-featured web app accessible from any device
- **All Desktop Features**: Summarize, extract, generate audio, and manage scheduler from the browser
- **In-App Guide**: Built-in user guide accessible from the header
- **Tooltips**: Hover over any field for helpful guidance

### Additional Features
- **API Key Management**: Save, view, copy, and manage your API key securely
- **Transcription Support**: Transcribe audio files using faster-whisper (if installed on your system)

---

## Quick Start

1. **Launch the app**
2. **Enter your Gemini API key** and click 💾 to save
3. **Configure news sources**: Click "Edit Sources" to add YouTube channels
4. **Fetch news**: Set date range and click "Get YouTube News"
5. **Generate audio**: Choose Fast (gTTS) or Quality (Kokoro) audio generation

---

## Building from Source

For developers who want to build the app themselves:

### Prerequisites
- Python 3.10+
- pip

### Setup
```bash
git clone https://github.com/wcfcarolina13/News-Summarizer.git
cd News-Summarizer/daily_audio_briefing
pip install -r requirements-desktop.txt
```

### Run from Source
```bash
python gui_app.py
```

### Build Installers

**macOS:**
```bash
python build_app.py
./create_dmg.sh
```

**Windows:**
```bash
build_windows.bat
```

Or use GitHub Actions - push a version tag to automatically build both installers:
```bash
git tag v1.0.0
git push --tags
```

---

## Web Dashboard (Server Mode)

The web dashboard provides a mobile-friendly interface for all features, plus an automated scheduler for hands-free data extraction.

### Running Locally

```bash
cd daily_audio_briefing
pip install -r requirements-server.txt
python web_app.py
# Opens at http://localhost:5001
```

### Deploy to Render.com (Free Tier)

1. Push to GitHub (use the `server-deploy` branch)
2. Create a new Web Service on [Render.com](https://render.com)
3. Connect your GitHub repository
4. Configure:
   - **Root Directory**: `daily_audio_briefing`
   - **Build Command**: `pip install -r requirements-server.txt`
   - **Start Command**: `gunicorn web_app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`
5. Set environment variables in Render dashboard:
   - `SERVER_MODE=true` — Enables auto-start of scheduler
   - `GEMINI_API_KEY` — Your Google Gemini API key
   - `GOOGLE_CREDENTIALS_JSON` — Full JSON of service account credentials (for Sheets export)
6. Deploy

### Keep-Alive

Render's free tier sleeps after 15 minutes of inactivity. The app includes a built-in self-ping that uses the `RENDER_EXTERNAL_URL` env var (auto-set by Render). For additional reliability, set up [UptimeRobot](https://uptimerobot.com) (free) to ping your `/health` endpoint every 5 minutes.

> **Note**: The web dashboard is currently in alpha testing. API keys and Google credentials are managed by the admin. There is no authentication on the web interface.

---

## Model Options

| Model | Speed | Limits |
|-------|-------|--------|
| `gemini-2.0-flash-exp` | Fastest | 4000 requests/min |
| `gemini-1.5-flash` | Balanced | 1500 requests/day |
| `gemini-1.5-pro` | Highest quality | 50 requests/day |

---

## Supported Sources

- **YouTube channels** (any public channel)
- **Substack** newsletters
- **Beehiiv** newsletters
- **Medium** articles
- **News sites** (CoinDesk, CoinTelegraph, Bloomberg, etc.)
- **Most article-based websites**

---

## Command Line Guide (Power Users)

For users who prefer command-line tools, several scripts can be run directly:

### ExecSum Newsletter Processor

Process ExecSum newsletters to extract market news for audio briefings:

```bash
cd daily_audio_briefing

# Process a single newsletter URL
python execsum_processor.py "https://execsum.beehiiv.com/p/your-newsletter-url"

# Process multiple URLs at once
python execsum_processor.py "https://url1" "https://url2" "https://url3"

# Process URLs from a file (one URL per line)
python execsum_processor.py --urls-file my_urls.txt

# Skip AI processing (basic extraction only)
python execsum_processor.py "https://url" --no-ai

# Custom output path
python execsum_processor.py "https://url" --output my_output.txt
```

Output files are saved to `Week_X_YYYY/execsum_digest_YYYY-MM-DD_HHMM.txt` by default.

### YouTube News Fetcher

Fetch and summarize videos from configured YouTube channels:

```bash
# Fetch last 7 days of videos
python get_youtube_news.py --days 7

# Fetch specific number of videos
python get_youtube_news.py --videos 10

# Fetch from date range
python get_youtube_news.py --start 2026-01-01 --end 2026-01-15
```

### Audio Generation

Generate audio from text files:

```bash
# Fast generation with gTTS
python make_audio.py input.txt output.mp3

# High-quality with Kokoro TTS
python make_audio_quality.py input.txt output.wav --voice af_sarah
```

### Main GUI Application

```bash
# Launch the desktop app from source
python gui_app.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No summaries generated | Check that sources.json has valid YouTube channel URLs |
| API errors | Verify your API key is correct (click 👁 to check) |
| "API key expired" | Get a new key at aistudio.google.com |
| No audio output | Check gui_log.txt for error details |
| Article fetch failed | Some sites block automated access; try pasting content directly |
| Transcription not available | Install faster-whisper: `pip install faster-whisper` |
| Port 5001 in use (web app) | Set `PORT` env var: `PORT=5002 python web_app.py` |
| Scheduler task disappears (Render) | Render's free tier has ephemeral storage — tasks reset on redeploy |
| Sheets export fails | Ensure `GOOGLE_CREDENTIALS_JSON` is set and the service account has sheet access |

---

## Architecture

| File | Purpose |
|------|---------|
| `gui_app.py` | Main desktop GUI application (Tkinter) |
| `web_app.py` | Flask web dashboard (server mode) |
| `server_scheduler.py` | Flask-integrated scheduler for cloud deployment |
| `scheduler.py` | Automated extraction task scheduler |
| `data_csv_processor.py` | Data extraction and Grid enrichment |
| `source_fetcher.py` | Unified content fetching (YouTube, RSS, articles) |
| `source_processor.py` | Source type routing |
| `execsum_processor.py` | ExecSum newsletter processing |
| `get_youtube_news.py` | YouTube fetching and summarization |
| `sheets_manager.py` | Google Sheets export |
| `audio_generator.py` | Audio generation orchestration |
| `make_audio_quality.py` | High-quality Kokoro TTS |
| `voice_manager.py` | Voice preset management |
| `file_manager.py` | File I/O with frozen app support |
| `transcription_service.py` | Audio transcription with system Python detection |

**Config files**: `sources.json`, `instruction_profiles.json`, `scheduled_tasks.json`, `settings.json`
**Extraction configs**: `extraction_instructions/*.json` (per-source extraction rules)

---

## Roadmap

1. **Alpha (Current)** — Admin-hosted. API keys and credentials managed centrally. macOS desktop app only.
2. **User Accounts** — Login system. Per-user API keys and Google credentials. Windows desktop build.
3. **Full Cloud** — Server-side audio generation. All features available via web browser.
4. **SaaS** — Multi-tenant platform. Per-user billing, subscription tiers, mobile apps.

---

## License

This project is provided as-is for personal use.

---

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/wcfcarolina13/News-Summarizer).
