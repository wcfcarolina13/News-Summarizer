# Daily Audio Briefing

A desktop application that creates personalized audio news briefings from YouTube channels, articles, and newsletters using AI summarization and text-to-speech.

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

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No summaries generated | Check that channels.txt has valid YouTube channel URLs |
| API errors | Verify your API key is correct (click 👁 to check) |
| "API key expired" | Get a new key at aistudio.google.com |
| No audio output | Check gui_log.txt for error details |
| Article fetch failed | Some sites block automated access; try pasting content directly |
| Transcription not available | Install faster-whisper: `pip install faster-whisper` |

---

## Architecture

| File | Purpose |
|------|---------|
| `gui_app.py` | Main GUI application |
| `transcription_service.py` | Audio transcription with system Python detection |
| `file_manager.py` | File I/O operations |
| `audio_generator.py` | Audio generation |
| `voice_manager.py` | Voice preset management |
| `data_csv_processor.py` | Data extraction and enrichment |
| `sheets_manager.py` | Google Sheets integration |
| `get_youtube_news.py` | YouTube fetching and summarization |
| `make_audio_quality.py` | High-quality Kokoro TTS |

---

## License

This project is provided as-is for personal use.

---

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/wcfcarolina13/News-Summarizer).
