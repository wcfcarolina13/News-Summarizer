# Building Daily Audio Briefing

This guide explains how to build the Daily Audio Briefing desktop application for macOS, Windows, and Linux.

## Prerequisites

### All Platforms
- Python 3.8 or higher
- pip (Python package manager)

### Platform-Specific
- **macOS**: Xcode command line tools (`xcode-select --install`)
- **Windows**: Visual Studio Build Tools (for some Python packages)
- **Linux**: `build-essential` package

## Quick Build

```bash
# Navigate to the app directory
cd daily_audio_briefing

# Build for your current platform
python3 build_app.py
```

The built application will be in the `dist/` folder.

## Build Options

```bash
# Clean previous builds first
python3 build_app.py --clean

# Install dependencies before building
python3 build_app.py --install

# Full clean rebuild
python3 build_app.py --clean --install
```

## Output Locations

| Platform | Output |
|----------|--------|
| macOS | `dist/Daily Audio Briefing.app` |
| Windows | `dist/DailyAudioBriefing.exe` |
| Linux | `dist/daily-audio-briefing` |

## Distribution

### macOS
1. Build the app: `python3 build_app.py`
2. Create a DMG (optional):
   ```bash
   hdiutil create -volname "Daily Audio Briefing" -srcfolder "dist/Daily Audio Briefing.app" -ov -format UDZO "DailyAudioBriefing.dmg"
   ```
3. Or zip for distribution: `zip -r DailyAudioBriefing-mac.zip "dist/Daily Audio Briefing.app"`

### Windows
1. Build on a Windows machine: `python build_app.py`
2. The `.exe` file can be distributed directly
3. For an installer, consider using NSIS or Inno Setup

### Linux
1. Build on a Linux machine: `python3 build_app.py`
2. Distribute as AppImage or create a `.deb` package

## User Requirements

Users running the built application need:

1. **FFmpeg** - Required for audio conversion
   - macOS: `brew install ffmpeg`
   - Windows: Download from https://ffmpeg.org or `choco install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

2. **Gemini API Key** - For AI summarization
   - Get a free key at https://aistudio.google.com/apikey
   - Enter it in the app's Settings

3. **Google Sheets (Optional)** - For direct export
   - See "Google Sheets Setup" section below

## Google Sheets Setup (Optional)

For non-technical users, the easiest way to get data into Google Sheets is:
1. Export as CSV from the app
2. Open Google Sheets > File > Import > Upload

For automatic export:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable "Google Sheets API"
4. Go to IAM & Admin > Service Accounts
5. Create a service account
6. Download the JSON key file
7. Save it as `google_credentials.json` in the app folder
8. Share your Google Sheet with the service account email

## Troubleshooting

### Build Fails with Missing Module
```bash
pip install -r requirements-desktop.txt
```

### App Won't Launch on macOS
If you get "App is damaged" or security warnings:
```bash
xattr -cr "dist/Daily Audio Briefing.app"
```
Or go to System Settings > Privacy & Security and allow the app.

### Missing FFmpeg Error
The app requires FFmpeg for audio features. Install it:
- macOS: `brew install ffmpeg`
- Windows: `choco install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Large App Size
The app bundles Python and all dependencies (~300MB). This is normal for PyInstaller builds.

## Building for Another Platform

PyInstaller can only create executables for the platform it runs on. To build for Windows:
1. Set up a Windows machine or VM
2. Install Python and dependencies
3. Run `python build_app.py`

For CI/CD, consider using GitHub Actions with matrix builds for multiple platforms.

## Development vs Production

For development, run the app directly:
```bash
python3 gui_app.py
```

Only build with PyInstaller when creating a distributable version.
