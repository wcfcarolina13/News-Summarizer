# Daily Audio Briefing

A desktop application for generating daily audio news summaries from YouTube channels using AI summarization.

## Features

- **YouTube News Aggregation**: Fetches and summarizes videos from configured YouTube channels
- **AI-Powered Summarization**: Uses Google Gemini AI to create concise, audio-friendly summaries
- **Multiple Audio Formats**: Generate audio in both fast (gTTS) and high-quality (Kokoro TTS) modes
- **Date Range Processing**: Fetch news from specific date ranges or recent days
- **Batch Audio Conversion**: Convert multiple daily summaries to audio at once
- **Voice Selection**: Choose from multiple voice presets for high-quality audio generation
- **Source Management**: Easy-to-use interface for managing YouTube channel sources

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
   - Copy `.env.example` to `.env`
   - Add your Gemini API key to `.env`:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```
   - Get a free API key at: https://makersuite.google.com/app/apikey

4. Configure your news sources:
   - Add YouTube channel URLs to `channels.txt` (one per line)
   - Or use the GUI "Edit Sources" button for easier management

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

### Using the GUI

1. **Enter API Key**: Paste your Gemini API key in the top field (saved automatically)

2. **Select Model**: Choose from:
   - Fast (FREE): 4000 requests/min
   - Balanced (FREE): 1500 requests/day
   - Best (FREE, 50/day): Highest quality

3. **Fetch News**:
   - Set days to fetch (default: 7 days)
   - Or enable "Use date range" and select specific dates using calendar buttons
   - Click "Get YouTube News" to fetch and summarize

4. **Edit Sources**: Click "Edit Sources" to:
   - Enable/disable channels
   - Add new channel URLs
   - Bulk import multiple channels

5. **Generate Audio**:
   - **Fast Generation**: Click "Generate Fast (gTTS)" for quick text-to-speech
   - **Quality Generation**: 
     - Select a voice from the dropdown
     - Click "Play Sample" to preview
     - Click "Generate Quality (Kokoro)" for high-quality audio

6. **Batch Convert**: Click "Convert Selected Dates to Audio" to convert multiple daily summaries to audio files

### File Organization

- Summaries are organized in `Week_*` folders by week number
- Individual daily summaries: `summary_YYYY-MM-DD.txt`
- Audio files: `daily_fast.mp3` (fast) or `daily_quality.wav` (high-quality)
- Check logs in `gui_log.txt` if issues occur

### Command Line Usage

You can also run scripts directly:

```bash
# Fetch news for the last 7 days
python get_youtube_news.py --days 7

# Fetch news for a specific date range
python get_youtube_news.py --start 2024-12-01 --end 2024-12-07

# Use a specific model
python get_youtube_news.py --days 7 --model gemini-2.5-pro

# Generate fast audio
python make_audio_fast.py

# Generate quality audio with specific voice
python make_audio_quality.py --voice af_sarah --input summary.txt --output output.wav
```

## Model Options

- `gemini-2.5-flash`: Fastest, 4000 requests/min (default)
- `gemini-2.5-pro`: Highest quality, 50 requests/day

## Available Voices

High-quality voices are located in the `voices/` directory. Preview any voice using the "Play Sample" button in the GUI.

## Troubleshooting

- **No summaries generated**: Check that channels.txt has valid YouTube channel URLs
- **API errors**: Verify your API key is correct in .env
- **No audio output**: Check gui_log.txt for error details
- **Missing transcripts**: Some videos may not have captions available

## Notes

- The AI skips duplicate content and promotional videos automatically
- Summaries are optimized for audio playback (no bullet points, natural speech)
- Generated files are organized weekly for easy management
- Calendar buttons allow easy date selection for date range queries

## Progress

✅ GUI application with improved date range controls
✅ Calendar button positioning fixed for better UX
✅ Multi-model support (Flash, Pro)
✅ Batch audio conversion for historical summaries
✅ Source management interface
✅ Voice preview system

Ready for production use!
