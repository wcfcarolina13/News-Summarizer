"""
Daily Audio Briefing - Mobile Web Application

Full-featured web interface for the News Summarizer, designed for mobile access.
Replicates all desktop GUI functionality with a responsive interface.

Features:
- YouTube news summarization
- Audio generation (Fast/Quality)
- Data CSV extraction from newsletters
- File transcription
- Source management
- Custom instructions

Run: python web_app.py
Deploy: See Procfile, railway.json, render.yaml
"""

import os
import sys
import json
import uuid
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template_string, request, jsonify,
    send_file, Response, redirect, url_for, session
)

# Import existing modules
from file_manager import FileManager
from voice_manager import VoiceManager

# Import CSV processor
try:
    from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions
    CSV_PROCESSOR_AVAILABLE = True
except ImportError:
    CSV_PROCESSOR_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Base directory
BASE_DIR = Path(__file__).parent

# Initialize managers
file_manager = FileManager()
voice_manager = VoiceManager()

# Task storage (in-memory; use Redis/DB for production)
tasks = {}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_week_folder():
    """Get current week's folder name."""
    now = datetime.now()
    week_num = now.isocalendar()[1]
    return f"Week_{week_num}_{now.year}"

def get_recent_summaries(limit=10):
    """Get recent summary files."""
    summaries = []

    # Look in Week_* folders
    for folder in sorted(BASE_DIR.glob("Week_*"), reverse=True):
        if folder.is_dir():
            for f in sorted(folder.glob("summary_*.txt"), reverse=True):
                try:
                    content = f.read_text()[:500]
                    summaries.append({
                        'name': f.name,
                        'folder': folder.name,
                        'path': str(f),
                        'date': f.stem.replace('summary_', ''),
                        'preview': content[:200] + '...' if len(content) > 200 else content,
                        'has_audio': (folder / f.stem.replace('summary', 'audio_quality') + '.wav').exists() or
                                    (folder / f.stem.replace('summary', 'audio_quality') + '.mp3').exists()
                    })
                except:
                    pass

                if len(summaries) >= limit:
                    break
        if len(summaries) >= limit:
            break

    return summaries

def load_sources():
    """Load YouTube sources from sources.json."""
    sources_path = BASE_DIR / 'sources.json'
    if sources_path.exists():
        try:
            with open(sources_path) as f:
                data = json.load(f)
                return data.get('sources', [])
        except:
            pass

    # Fallback to channels.txt
    channels_path = BASE_DIR / 'channels.txt'
    if channels_path.exists():
        try:
            lines = channels_path.read_text().strip().split('\n')
            return [{'url': line.strip(), 'enabled': True} for line in lines if line.strip()]
        except:
            pass

    return []

def save_sources(sources):
    """Save sources to sources.json."""
    sources_path = BASE_DIR / 'sources.json'
    with open(sources_path, 'w') as f:
        json.dump({'sources': sources}, f, indent=2)

def load_custom_instructions_text():
    """Load custom instructions."""
    path = BASE_DIR / 'custom_instructions.txt'
    if path.exists():
        return path.read_text()
    return ""

def save_custom_instructions_text(text):
    """Save custom instructions."""
    path = BASE_DIR / 'custom_instructions.txt'
    path.write_text(text)

def check_dependencies():
    """Check available dependencies."""
    deps = {
        'ffmpeg': False,
        'faster_whisper': False,
        'kokoro': False
    }

    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        deps['ffmpeg'] = True
    except:
        pass

    # Check faster-whisper
    try:
        import faster_whisper
        deps['faster_whisper'] = True
    except:
        pass

    # Check kokoro
    kokoro_path = BASE_DIR / 'kokoro-v1.0.onnx'
    deps['kokoro'] = kokoro_path.exists()

    return deps

def run_script_async(script_name, args, env_vars=None, task_id=None):
    """Run a Python script asynchronously."""
    def runner():
        try:
            tasks[task_id]['status'] = 'running'
            tasks[task_id]['started_at'] = datetime.now().isoformat()

            cmd = [sys.executable, str(BASE_DIR / script_name)] + args
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(BASE_DIR)
            )

            stdout, stderr = process.communicate(timeout=3600)

            tasks[task_id]['status'] = 'completed' if process.returncode == 0 else 'failed'
            tasks[task_id]['returncode'] = process.returncode
            tasks[task_id]['stdout'] = stdout.decode('utf-8', errors='ignore')[-2000:]
            tasks[task_id]['stderr'] = stderr.decode('utf-8', errors='ignore')[-2000:]
            tasks[task_id]['completed_at'] = datetime.now().isoformat()

        except subprocess.TimeoutExpired:
            tasks[task_id]['status'] = 'timeout'
            tasks[task_id]['error'] = 'Task timed out after 1 hour'
        except Exception as e:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = str(e)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread

# =============================================================================
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Daily Audio Briefing</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0f0f0f">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <style>
        :root {
            --bg-primary: #0f0f0f;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #252525;
            --text-primary: #ffffff;
            --text-secondary: #aaaaaa;
            --text-muted: #666666;
            --accent: #4a9eff;
            --accent-hover: #3a8eef;
            --success: #2ecc71;
            --warning: #f39c12;
            --danger: #e74c3c;
            --border: #333333;
        }

        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            padding-bottom: 80px;
        }

        /* Navigation */
        .nav-bottom {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-around;
            padding: 8px 0;
            z-index: 1000;
        }

        .nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 8px 16px;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.7rem;
            transition: color 0.2s;
        }

        .nav-item.active, .nav-item:hover {
            color: var(--accent);
        }

        .nav-item svg {
            width: 24px;
            height: 24px;
            margin-bottom: 4px;
        }

        /* Header */
        .header {
            background: var(--bg-secondary);
            padding: 16px;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header h1 {
            margin: 0;
            font-size: 1.25rem;
            font-weight: 600;
        }

        .header .subtitle {
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-top: 4px;
        }

        /* Container */
        .container {
            padding: 16px;
            max-width: 800px;
            margin: 0 auto;
        }

        /* Cards */
        .card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }

        .card-title {
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-title svg {
            width: 18px;
            height: 18px;
            color: var(--accent);
        }

        /* Form Elements */
        label {
            display: block;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }

        input, textarea, select {
            width: 100%;
            padding: 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 16px;
            margin-bottom: 12px;
        }

        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: var(--accent);
        }

        textarea {
            min-height: 120px;
            resize: vertical;
            font-family: inherit;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 14px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            width: 100%;
            margin-bottom: 8px;
        }

        .btn-primary {
            background: var(--accent);
            color: white;
        }

        .btn-primary:hover, .btn-primary:active {
            background: var(--accent-hover);
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-success {
            background: var(--success);
            color: white;
        }

        .btn-warning {
            background: var(--warning);
            color: white;
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-row {
            display: flex;
            gap: 8px;
        }

        .btn-row .btn {
            flex: 1;
        }

        /* Status */
        .status {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 0.9rem;
            display: none;
        }

        .status.show { display: block; }
        .status.info { background: #1e3a5f; color: var(--accent); }
        .status.success { background: #1e3f2e; color: var(--success); }
        .status.warning { background: #3f3a1e; color: var(--warning); }
        .status.error { background: #3f1e1e; color: var(--danger); }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid currentColor;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Summary Cards */
        .summary-card {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 3px solid var(--accent);
        }

        .summary-card .date {
            font-size: 0.75rem;
            color: var(--accent);
            margin-bottom: 4px;
        }

        .summary-card .preview {
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        .summary-card .folder {
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 8px;
        }

        /* Source List */
        .source-item {
            display: flex;
            align-items: center;
            padding: 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            margin-bottom: 8px;
        }

        .source-item input[type="checkbox"] {
            width: 20px;
            height: 20px;
            margin: 0;
            margin-right: 12px;
        }

        .source-item .url {
            flex: 1;
            font-size: 0.85rem;
            word-break: break-all;
        }

        .source-item .delete-btn {
            background: none;
            border: none;
            color: var(--danger);
            padding: 8px;
            cursor: pointer;
        }

        /* Tabs */
        .tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 16px;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        .tab {
            padding: 10px 16px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-secondary);
            font-size: 0.85rem;
            cursor: pointer;
            white-space: nowrap;
            flex-shrink: 0;
        }

        .tab.active {
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }

        /* Mode Selector */
        .mode-selector {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }

        .mode-option {
            flex: 1;
            padding: 10px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            text-align: center;
            font-size: 0.85rem;
            cursor: pointer;
        }

        .mode-option.active {
            border-color: var(--accent);
            color: var(--accent);
        }

        /* Toggle */
        .toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }

        .toggle-row:last-child {
            border-bottom: none;
        }

        .toggle {
            width: 50px;
            height: 28px;
            background: var(--bg-tertiary);
            border-radius: 14px;
            position: relative;
            cursor: pointer;
            transition: background 0.2s;
        }

        .toggle.active {
            background: var(--accent);
        }

        .toggle::after {
            content: '';
            position: absolute;
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            top: 3px;
            left: 3px;
            transition: transform 0.2s;
        }

        .toggle.active::after {
            transform: translateX(22px);
        }

        /* Dependency Status */
        .dep-status {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }

        .dep-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: var(--bg-tertiary);
            border-radius: 16px;
            font-size: 0.75rem;
        }

        .dep-badge .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .dep-badge .dot.green { background: var(--success); }
        .dep-badge .dot.orange { background: var(--warning); }
        .dep-badge .dot.red { background: var(--danger); }

        /* Results List */
        .result-item {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 3px solid var(--accent);
        }

        .result-item .category {
            font-size: 0.7rem;
            color: var(--accent);
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .result-item .title {
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 4px;
        }

        .result-item .url {
            font-size: 0.75rem;
            color: var(--text-muted);
            word-break: break-all;
        }

        .result-item a {
            color: inherit;
            text-decoration: none;
        }

        /* Audio Player */
        .audio-player {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }

        .audio-player audio {
            width: 100%;
            margin-top: 8px;
        }

        /* Hidden */
        .hidden { display: none !important; }

        /* Page sections */
        .page { display: none; }
        .page.active { display: block; }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-muted);
        }

        .empty-state svg {
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }

        /* ========================================
           DESKTOP RESPONSIVE STYLES (768px+)
           ======================================== */
        @media (min-width: 768px) {
            body {
                padding-bottom: 0;
                padding-left: 240px;
            }

            /* Sidebar Navigation */
            .nav-bottom {
                position: fixed;
                top: 0;
                left: 0;
                bottom: 0;
                right: auto;
                width: 240px;
                flex-direction: column;
                justify-content: flex-start;
                padding: 20px 0;
                border-top: none;
                border-right: 1px solid var(--border);
            }

            .nav-item {
                flex-direction: row;
                justify-content: flex-start;
                padding: 14px 24px;
                font-size: 0.9rem;
                gap: 12px;
            }

            .nav-item svg {
                margin-bottom: 0;
            }

            /* Sidebar Logo */
            .nav-bottom::before {
                content: 'Daily Audio Briefing';
                display: block;
                font-size: 1.1rem;
                font-weight: 700;
                padding: 0 24px 24px;
                margin-bottom: 8px;
                border-bottom: 1px solid var(--border);
                color: var(--accent);
            }

            /* Header adjustments */
            .header {
                padding: 20px 32px;
            }

            .header h1 {
                font-size: 1.5rem;
            }

            /* Container - wider on desktop */
            .container {
                padding: 24px 32px;
                max-width: 1200px;
            }

            /* Card grid for desktop */
            .page.active {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                align-items: start;
            }

            .page .card {
                margin-bottom: 0;
            }

            /* Full-width cards for forms */
            .page .card:has(form),
            .page .card:has(input),
            .page .card:has(select),
            .page .card:has(textarea),
            #page-extract .card,
            #page-summarize .card,
            #page-audio .card,
            #page-settings .card {
                grid-column: 1 / -1;
                max-width: 800px;
            }

            /* Two-column form layout */
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }

            /* Larger buttons */
            .btn {
                padding: 14px 24px;
                font-size: 0.95rem;
            }

            /* Larger inputs */
            input, select, textarea {
                padding: 14px;
                font-size: 0.95rem;
            }

            /* Card hover effect */
            .card {
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            }

            /* Results table layout */
            .result-item {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: center;
            }
        }

        /* ========================================
           LARGE DESKTOP (1200px+)
           ======================================== */
        @media (min-width: 1200px) {
            body {
                padding-left: 280px;
            }

            .nav-bottom {
                width: 280px;
            }

            .nav-item {
                padding: 16px 28px;
                font-size: 0.95rem;
            }

            .nav-bottom::before {
                padding: 0 28px 28px;
                font-size: 1.2rem;
            }

            .container {
                padding: 32px 48px;
                max-width: 1400px;
            }

            .card {
                padding: 24px;
                border-radius: 16px;
            }

            .card-title {
                font-size: 1rem;
                margin-bottom: 16px;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>Daily Audio Briefing</h1>
        <div class="subtitle" id="headerSubtitle">Mobile Web Interface</div>
    </div>

    <!-- Status Bar -->
    <div class="container">
        <div class="status" id="globalStatus"></div>
    </div>

    <!-- Pages -->
    <div class="container">
        <!-- Home Page -->
        <div class="page active" id="page-home">
            <div class="card">
                <div class="card-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>
                    Quick Actions
                </div>
                <button class="btn btn-primary" data-nav="summarize">
                    <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                    Get YouTube News
                </button>
                <button class="btn btn-secondary" data-nav="extract">
                    <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    Extract from Newsletter
                </button>
                <button class="btn btn-secondary" data-nav="audio">
                    <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
                    Generate Audio
                </button>
            </div>

            <div class="card">
                <div class="card-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    Recent Summaries
                </div>
                <div id="recentSummaries">
                    <div class="empty-state">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                        <p>No summaries yet</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Summarize Page -->
        <div class="page" id="page-summarize">
            <div class="card">
                <div class="card-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                    YouTube Summarization
                </div>

                <label>Gemini API Key</label>
                <input type="password" id="apiKey" placeholder="Enter your Gemini API key">

                <label>Model</label>
                <select id="model">
                    <option value="fast">Fast (FREE) - 4000 req/min</option>
                    <option value="balanced">Balanced (FREE) - 1500 req/day</option>
                    <option value="best">Best (FREE) - 50 req/day</option>
                </select>

                <label>Fetch Mode</label>
                <div class="mode-selector">
                    <div class="mode-option active" onclick="setMode('days')">Days</div>
                    <div class="mode-option" onclick="setMode('hours')">Hours</div>
                    <div class="mode-option" onclick="setMode('urls')">URLs</div>
                </div>

                <div id="fetchValueSection">
                    <label id="fetchLabel">Number of Days</label>
                    <input type="number" id="fetchValue" value="7" min="1">
                </div>

                <div id="urlsSection" class="hidden">
                    <label>YouTube URLs (one per line)</label>
                    <textarea id="urls" placeholder="https://youtube.com/watch?v=..."></textarea>
                </div>

                <div id="sourceCount" style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 12px;">
                    Loading sources...
                </div>

                <button class="btn btn-primary" id="fetchBtn" onclick="startFetch()">
                    <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                    Fetch & Summarize
                </button>
            </div>

            <div class="card" id="summaryCard" style="display: none;">
                <div class="card-title">Summary</div>
                <textarea id="summaryText" style="min-height: 200px;"></textarea>
                <div class="btn-row">
                    <button class="btn btn-secondary" onclick="saveSummary()">Save</button>
                    <button class="btn btn-success" data-nav="audio">Generate Audio</button>
                </div>
            </div>
        </div>

        <!-- Extract Page (CSV Processor) -->
        <div class="page" id="page-extract">
            <div class="card">
                <div class="card-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
                    Extract from Newsletter
                </div>

                <div class="tabs">
                    <div class="tab active" onclick="setExtractMode('url')">URL</div>
                    <div class="tab" onclick="setExtractMode('html')">Paste HTML</div>
                </div>

                <div id="extractUrlSection">
                    <label>Newsletter URL</label>
                    <input type="text" id="extractUrl" placeholder="https://cryptosum.beehiiv.com/p/...">
                </div>

                <div id="extractHtmlSection" class="hidden">
                    <label>Paste HTML Content</label>
                    <textarea id="extractHtml" placeholder="Paste HTML source here..."></textarea>
                    <label>Source URL (optional)</label>
                    <input type="text" id="extractSourceUrl" placeholder="https://...">
                </div>

                <label>Config</label>
                <select id="extractConfig">
                    <option value="default">Default (all links)</option>
                    <option value="cryptosum">CryptoSum Newsletter</option>
                </select>

                <div class="toggle-row" style="margin: 12px 0;">
                    <span>Enrich with The Grid data</span>
                    <div class="toggle" id="gridToggle" onclick="toggleGrid()"></div>
                </div>
                <p style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 12px;">
                    Match entities to The Grid's Web3 database and add TGS recommendations
                </p>

                <button class="btn btn-primary" onclick="startExtract()">
                    Extract Links
                </button>
            </div>

            <div class="card" id="extractResults" style="display: none;">
                <div class="card-title">
                    Extracted Links (<span id="extractCount">0</span>)
                </div>
                <div class="btn-row">
                    <button class="btn btn-success" onclick="downloadExtractedCSV()">
                        Download CSV
                    </button>
                    <button class="btn btn-secondary" onclick="copyExtractedText()">
                        Copy Text
                    </button>
                </div>
                <div id="extractList" style="margin-top: 12px;"></div>
            </div>
        </div>

        <!-- Audio Page -->
        <div class="page" id="page-audio">
            <div class="card">
                <div class="card-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
                    Generate Audio
                </div>

                <div class="dep-status" id="depStatus">
                    <!-- Filled by JS -->
                </div>

                <label>Voice (for Quality mode)</label>
                <select id="voice">
                    <option value="af_sarah">af_sarah (Female)</option>
                    <option value="af_bella">af_bella (Female)</option>
                    <option value="am_adam">am_adam (Male)</option>
                    <option value="am_michael">am_michael (Male)</option>
                </select>

                <button class="btn btn-secondary" onclick="playSample()">
                    ▶ Play Sample
                </button>

                <div class="btn-row" style="margin-top: 12px;">
                    <button class="btn btn-primary" onclick="generateAudio('fast')">
                        Fast (gTTS)
                    </button>
                    <button class="btn btn-success" onclick="generateAudio('quality')">
                        Quality (Kokoro)
                    </button>
                </div>
            </div>

            <div class="card" id="audioPlayerCard" style="display: none;">
                <div class="card-title">Generated Audio</div>
                <audio id="audioPlayer" controls></audio>
                <button class="btn btn-secondary" style="margin-top: 12px;" onclick="downloadAudio()">
                    Download Audio
                </button>
            </div>
        </div>

        <!-- Settings Page -->
        <div class="page" id="page-settings">
            <div class="card">
                <div class="card-title">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    Settings
                </div>

                <label>Gemini API Key</label>
                <input type="password" id="settingsApiKey" placeholder="sk-...">
                <button class="btn btn-secondary" onclick="saveApiKey()">Save API Key</button>
            </div>

            <div class="card">
                <div class="card-title">Custom Instructions</div>
                <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">
                    Personalize how Gemini summarizes content for you.
                </p>
                <textarea id="customInstructions" placeholder="I'm interested in crypto, AI, geopolitics..."></textarea>
                <button class="btn btn-secondary" onclick="saveCustomInstructions()">Save Instructions</button>
            </div>

            <div class="card">
                <div class="card-title">YouTube Sources</div>
                <div id="sourcesList"></div>
                <input type="text" id="newSourceUrl" placeholder="https://youtube.com/@channel/videos">
                <button class="btn btn-secondary" onclick="addSource()">Add Source</button>
            </div>

            <div class="card">
                <div class="card-title">System Status</div>
                <div class="dep-status" id="systemStatus"></div>
            </div>
        </div>
    </div>

    <!-- Bottom Navigation -->
    <nav class="nav-bottom" id="mainNav">
        <a class="nav-item active" href="#" data-page="home">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>
            <span>Home</span>
        </a>
        <a class="nav-item" href="#" data-page="summarize">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
            <span>News</span>
        </a>
        <a class="nav-item" href="#" data-page="extract">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
            <span>Extract</span>
        </a>
        <a class="nav-item" href="#" data-page="audio">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
            <span>Audio</span>
        </a>
        <a class="nav-item" href="#" data-page="settings">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            <span>Settings</span>
        </a>
    </nav>

    <script>
        // State
        let currentPage = 'home';
        let fetchMode = 'days';
        let extractMode = 'url';
        let extractedItems = [];
        let sources = [];
        let currentTaskId = null;

        // Navigation
        function navigateTo(page) {
            console.log('navigateTo called with:', page);
            try {
                // Hide all pages, show target page
                var pages = document.querySelectorAll('.page');
                console.log('Found pages:', pages.length);
                for (var i = 0; i < pages.length; i++) {
                    console.log('Removing active from:', pages[i].id);
                    pages[i].classList.remove('active');
                    pages[i].style.display = 'none';
                }
                var targetPage = document.getElementById('page-' + page);
                console.log('Target page element:', targetPage);
                if (targetPage) {
                    targetPage.classList.add('active');
                    console.log('Added active to:', targetPage.id);
                    // Force display
                    targetPage.style.display = 'block';
                } else {
                    console.error('Target page not found: page-' + page);
                }

                // Update nav highlighting
                var navItems = document.querySelectorAll('.nav-item');
                for (var j = 0; j < navItems.length; j++) {
                    navItems[j].classList.remove('active');
                    if (navItems[j].getAttribute('data-page') === page) {
                        navItems[j].classList.add('active');
                    }
                }

                currentPage = page;

                // Load page-specific data
                if (page === 'home') loadRecentSummaries();
                if (page === 'settings') loadSettings();
                if (page === 'summarize') loadSourceCount();
                if (page === 'audio') loadDependencies();
            } catch (e) {
                console.error('Navigation error:', e);
                alert('Nav error: ' + e.message);
            }
        }

        // Status messages
        function showStatus(message, type = 'info', spinner = false) {
            const status = document.getElementById('globalStatus');
            status.className = 'status show ' + type;
            status.innerHTML = (spinner ? '<span class="spinner"></span>' : '') + message;
        }

        function hideStatus() {
            document.getElementById('globalStatus').className = 'status';
        }

        // API calls
        async function api(endpoint, data = null) {
            const options = {
                method: data ? 'POST' : 'GET',
                headers: { 'Content-Type': 'application/json' }
            };
            if (data) options.body = JSON.stringify(data);

            const response = await fetch(endpoint, options);
            return response.json();
        }

        // Home page
        async function loadRecentSummaries() {
            try {
                const data = await api('/api/summaries');
                const container = document.getElementById('recentSummaries');

                if (data.summaries && data.summaries.length > 0) {
                    container.innerHTML = data.summaries.map(s => `
                        <div class="summary-card">
                            <div class="date">${s.date}</div>
                            <div class="preview">${s.preview}</div>
                            <div class="folder">${s.folder}</div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div class="empty-state"><p>No summaries yet. Start by fetching YouTube news!</p></div>';
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Summarize page
        function setMode(mode) {
            fetchMode = mode;
            document.querySelectorAll('.mode-option').forEach(m => m.classList.remove('active'));
            event.target.classList.add('active');

            const valueSection = document.getElementById('fetchValueSection');
            const urlsSection = document.getElementById('urlsSection');
            const label = document.getElementById('fetchLabel');

            if (mode === 'urls') {
                valueSection.classList.add('hidden');
                urlsSection.classList.remove('hidden');
            } else {
                valueSection.classList.remove('hidden');
                urlsSection.classList.add('hidden');
                label.textContent = mode === 'hours' ? 'Number of Hours' : 'Number of Days';
            }
        }

        async function loadSourceCount() {
            try {
                const data = await api('/api/sources');
                sources = data.sources || [];
                const enabled = sources.filter(s => s.enabled).length;
                document.getElementById('sourceCount').textContent =
                    `${enabled} of ${sources.length} sources enabled`;
            } catch (e) {
                console.error(e);
            }
        }

        async function startFetch() {
            const apiKey = document.getElementById('apiKey').value;
            if (!apiKey) {
                showStatus('Please enter your Gemini API key', 'error');
                return;
            }

            const model = document.getElementById('model').value;
            const value = document.getElementById('fetchValue').value;
            const urls = document.getElementById('urls').value;

            showStatus('Starting summarization...', 'info', true);
            document.getElementById('fetchBtn').disabled = true;

            try {
                const data = await api('/api/summarize', {
                    apiKey,
                    model,
                    mode: fetchMode,
                    value: parseInt(value) || 7,
                    urls: urls.split('\\n').filter(u => u.trim())
                });

                if (data.error) {
                    showStatus('Error: ' + data.error, 'error');
                } else {
                    currentTaskId = data.task_id;
                    pollTask(data.task_id);
                }
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }

            document.getElementById('fetchBtn').disabled = false;
        }

        async function pollTask(taskId) {
            try {
                const data = await api('/api/task/' + taskId);

                if (data.status === 'running') {
                    showStatus('Processing... This may take a few minutes.', 'info', true);
                    setTimeout(() => pollTask(taskId), 3000);
                } else if (data.status === 'completed') {
                    showStatus('Summarization complete!', 'success');
                    loadSummary();
                } else {
                    showStatus('Task failed: ' + (data.error || data.stderr || 'Unknown error'), 'error');
                }
            } catch (e) {
                showStatus('Error checking task status', 'error');
            }
        }

        async function loadSummary() {
            try {
                const data = await api('/api/summary');
                if (data.content) {
                    document.getElementById('summaryText').value = data.content;
                    document.getElementById('summaryCard').style.display = 'block';
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function saveSummary() {
            const content = document.getElementById('summaryText').value;
            try {
                await api('/api/summary', { content });
                showStatus('Summary saved!', 'success');
                setTimeout(hideStatus, 2000);
            } catch (e) {
                showStatus('Error saving summary', 'error');
            }
        }

        // Extract page
        function setExtractMode(mode) {
            extractMode = mode;
            document.querySelectorAll('#page-extract .tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            document.getElementById('extractUrlSection').classList.toggle('hidden', mode !== 'url');
            document.getElementById('extractHtmlSection').classList.toggle('hidden', mode !== 'html');
        }

        let enrichGrid = false;

        function toggleGrid() {
            enrichGrid = !enrichGrid;
            document.getElementById('gridToggle').classList.toggle('active', enrichGrid);
        }

        async function startExtract() {
            const config = document.getElementById('extractConfig').value;

            let requestData = {
                mode: extractMode,
                config,
                enrichGrid
            };

            if (extractMode === 'url') {
                requestData.url = document.getElementById('extractUrl').value;
            } else {
                requestData.html = document.getElementById('extractHtml').value;
                requestData.sourceUrl = document.getElementById('extractSourceUrl').value;
            }

            const statusMsg = enrichGrid ? 'Extracting links and enriching with Grid data...' : 'Extracting links...';
            showStatus(statusMsg, 'info', true);

            try {
                const data = await api('/api/extract', requestData);

                if (data.error) {
                    showStatus('Error: ' + data.error, 'error');
                } else {
                    extractedItems = data.items || [];
                    showExtractResults(extractedItems);
                    const matchedCount = extractedItems.filter(i => i.grid_matched).length;
                    let msg = 'Extracted ' + extractedItems.length + ' links';
                    if (enrichGrid) {
                        msg += ` (${matchedCount} matched in Grid)`;
                    }
                    showStatus(msg, 'success');
                }
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }
        }

        function showExtractResults(items) {
            document.getElementById('extractCount').textContent = items.length;
            document.getElementById('extractResults').style.display = 'block';

            document.getElementById('extractList').innerHTML = items.slice(0, 50).map(item => {
                const gridBadge = item.grid_matched
                    ? `<span style="background: var(--success); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; margin-left: 8px;">✓ Grid: ${item.grid_entity_name || 'Matched'}</span>`
                    : '';
                const tgsNote = item.tgs_recommendation
                    ? `<div style="font-size: 0.7rem; color: var(--accent); margin-top: 4px;">TGS: ${item.tgs_recommendation}</div>`
                    : '';
                return `
                    <div class="result-item">
                        <div class="category">${item.category || 'General'}${gridBadge}</div>
                        <div class="title">${item.title || 'Untitled'}</div>
                        <div class="url"><a href="${item.url}" target="_blank">${item.url}</a></div>
                        ${tgsNote}
                    </div>
                `;
            }).join('');
        }

        function downloadExtractedCSV() {
            if (!extractedItems.length) return;

            // Base headers
            let headers = ['title', 'url', 'category', 'source_name', 'date_published'];

            // Add Grid headers if any item has grid data
            const hasGridData = extractedItems.some(i => i.grid_matched !== undefined);
            if (hasGridData) {
                headers = [...headers, 'grid_matched', 'grid_entity_name', 'grid_entity_type', 'grid_category', 'tgs_recommendation'];
            }

            const rows = extractedItems.map(item =>
                headers.map(h => '"' + String(item[h] || '').replace(/"/g, '""') + '"').join(',')
            );
            const csv = [headers.join(','), ...rows].join('\\n');

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'extracted_' + new Date().toISOString().slice(0,10) + '.csv';
            a.click();
            URL.revokeObjectURL(url);
        }

        function copyExtractedText() {
            if (!extractedItems.length) return;

            const text = extractedItems.map(item => {
                let line = `[${item.category}] ${item.title}\n${item.url}`;
                if (item.grid_matched) {
                    line += `\n→ Grid: ${item.grid_entity_name} (${item.grid_entity_type})`;
                }
                if (item.tgs_recommendation) {
                    line += `\n→ TGS: ${item.tgs_recommendation}`;
                }
                return line;
            }).join('\n\n');

            navigator.clipboard.writeText(text).then(() => {
                showStatus('Copied to clipboard!', 'success');
                setTimeout(hideStatus, 2000);
            });
        }

        // Audio page
        async function loadDependencies() {
            try {
                const data = await api('/api/dependencies');
                const container = document.getElementById('depStatus');

                container.innerHTML = `
                    <div class="dep-badge">
                        <span class="dot ${data.ffmpeg ? 'green' : 'orange'}"></span>
                        ffmpeg
                    </div>
                    <div class="dep-badge">
                        <span class="dot ${data.kokoro ? 'green' : 'orange'}"></span>
                        Kokoro TTS
                    </div>
                `;

                // Also load voices
                const voicesData = await api('/api/voices');
                const voiceSelect = document.getElementById('voice');
                voiceSelect.innerHTML = voicesData.voices.map(v =>
                    `<option value="${v}">${v}</option>`
                ).join('');
            } catch (e) {
                console.error(e);
            }
        }

        async function playSample() {
            const voice = document.getElementById('voice').value;
            showStatus('Generating sample...', 'info', true);

            try {
                const response = await fetch('/api/audio/sample?voice=' + voice);
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const audio = new Audio(url);
                    audio.play();
                    hideStatus();
                } else {
                    showStatus('Could not generate sample', 'error');
                }
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }
        }

        async function generateAudio(type) {
            const voice = document.getElementById('voice').value;
            showStatus('Generating audio...', 'info', true);

            try {
                const data = await api('/api/audio/generate', { type, voice });

                if (data.error) {
                    showStatus('Error: ' + data.error, 'error');
                } else {
                    currentTaskId = data.task_id;
                    pollAudioTask(data.task_id);
                }
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }
        }

        async function pollAudioTask(taskId) {
            try {
                const data = await api('/api/task/' + taskId);

                if (data.status === 'running') {
                    showStatus('Generating audio... This may take a minute.', 'info', true);
                    setTimeout(() => pollAudioTask(taskId), 2000);
                } else if (data.status === 'completed') {
                    showStatus('Audio generated!', 'success');
                    loadLatestAudio();
                } else {
                    showStatus('Audio generation failed', 'error');
                }
            } catch (e) {
                showStatus('Error checking task status', 'error');
            }
        }

        async function loadLatestAudio() {
            try {
                const data = await api('/api/audio/latest');
                if (data.path) {
                    const player = document.getElementById('audioPlayer');
                    player.src = '/api/audio/file?path=' + encodeURIComponent(data.path);
                    document.getElementById('audioPlayerCard').style.display = 'block';
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Settings page
        async function loadSettings() {
            try {
                // Load API key status
                const apiData = await api('/api/settings/apikey');
                if (apiData.hasKey) {
                    document.getElementById('settingsApiKey').placeholder = '••••••••••••••••';
                }

                // Load custom instructions
                const instrData = await api('/api/settings/instructions');
                document.getElementById('customInstructions').value = instrData.instructions || '';

                // Load sources
                const sourcesData = await api('/api/sources');
                sources = sourcesData.sources || [];
                renderSources();

                // Load dependencies
                const depData = await api('/api/dependencies');
                document.getElementById('systemStatus').innerHTML = `
                    <div class="dep-badge">
                        <span class="dot ${depData.ffmpeg ? 'green' : 'red'}"></span>
                        ffmpeg
                    </div>
                    <div class="dep-badge">
                        <span class="dot ${depData.faster_whisper ? 'green' : 'orange'}"></span>
                        Whisper
                    </div>
                    <div class="dep-badge">
                        <span class="dot ${depData.kokoro ? 'green' : 'orange'}"></span>
                        Kokoro
                    </div>
                `;
            } catch (e) {
                console.error(e);
            }
        }

        function renderSources() {
            const container = document.getElementById('sourcesList');
            container.innerHTML = sources.map((s, i) => `
                <div class="source-item">
                    <input type="checkbox" ${s.enabled ? 'checked' : ''}
                           onchange="toggleSource(${i})">
                    <span class="url">${s.url}</span>
                    <button class="delete-btn" onclick="deleteSource(${i})">×</button>
                </div>
            `).join('');
        }

        async function toggleSource(index) {
            sources[index].enabled = !sources[index].enabled;
            await api('/api/sources', { sources });
        }

        async function deleteSource(index) {
            sources.splice(index, 1);
            await api('/api/sources', { sources });
            renderSources();
        }

        async function addSource() {
            const url = document.getElementById('newSourceUrl').value.trim();
            if (!url) return;

            sources.push({ url, enabled: true });
            await api('/api/sources', { sources });
            document.getElementById('newSourceUrl').value = '';
            renderSources();
        }

        async function saveApiKey() {
            const key = document.getElementById('settingsApiKey').value;
            if (!key) return;

            try {
                await api('/api/settings/apikey', { key });
                showStatus('API key saved!', 'success');
                setTimeout(hideStatus, 2000);
            } catch (e) {
                showStatus('Error saving API key', 'error');
            }
        }

        async function saveCustomInstructions() {
            const instructions = document.getElementById('customInstructions').value;

            try {
                await api('/api/settings/instructions', { instructions });
                showStatus('Instructions saved!', 'success');
                setTimeout(hideStatus, 2000);
            } catch (e) {
                showStatus('Error saving instructions', 'error');
            }
        }

        // Device detection
        function updateDeviceInfo() {
            var subtitle = document.getElementById('headerSubtitle');
            var width = window.innerWidth;
            if (width >= 1200) {
                subtitle.textContent = 'Desktop Web Interface';
            } else if (width >= 768) {
                subtitle.textContent = 'Tablet Web Interface';
            } else {
                subtitle.textContent = 'Mobile Web Interface';
            }
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded, setting up navigation...');
            loadRecentSummaries();
            updateDeviceInfo();
            window.addEventListener('resize', updateDeviceInfo);

            // Set up navigation with event delegation (works better on mobile)
            var nav = document.getElementById('mainNav');
            console.log('Nav element found:', nav);
            if (nav) {
                nav.addEventListener('click', function(e) {
                    console.log('Nav clicked, target:', e.target);
                    e.preventDefault();
                    e.stopPropagation();
                    var target = e.target.closest('.nav-item');
                    console.log('Closest nav-item:', target);
                    if (target) {
                        var page = target.getAttribute('data-page');
                        console.log('Navigating to:', page);
                        if (page) {
                            navigateTo(page);
                        }
                    }
                    return false;
                });
            }

            // Set up all buttons with data-nav attribute
            var navButtons = document.querySelectorAll('[data-nav]');
            console.log('Found nav buttons:', navButtons.length);
            for (var i = 0; i < navButtons.length; i++) {
                navButtons[i].addEventListener('click', function(e) {
                    var page = e.currentTarget.getAttribute('data-nav');
                    console.log('Button nav to:', page);
                    if (page) navigateTo(page);
                });
            }
        });
    </script>
</body>
</html>
'''

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/summaries')
def api_summaries():
    """Get recent summaries."""
    summaries = get_recent_summaries()
    return jsonify({'summaries': summaries})

@app.route('/api/summary', methods=['GET', 'POST'])
def api_summary():
    """Get or save current summary."""
    if request.method == 'POST':
        data = request.json
        file_manager.save_summary(data.get('content', ''))
        return jsonify({'success': True})
    else:
        content = file_manager.load_summary()
        return jsonify({'content': content})

@app.route('/api/sources', methods=['GET', 'POST'])
def api_sources():
    """Get or save sources."""
    if request.method == 'POST':
        data = request.json
        save_sources(data.get('sources', []))
        return jsonify({'success': True})
    else:
        sources = load_sources()
        return jsonify({'sources': sources})

@app.route('/api/summarize', methods=['POST'])
def api_summarize():
    """Start YouTube summarization task."""
    data = request.json

    api_key = data.get('apiKey')
    if not api_key:
        return jsonify({'error': 'API key required'}), 400

    # Build arguments
    args = []
    mode = data.get('mode', 'days')
    value = data.get('value', 7)

    if mode == 'days':
        args.extend(['--days', str(value)])
    elif mode == 'hours':
        args.extend(['--hours', str(value)])
    elif mode == 'urls':
        urls = data.get('urls', [])
        if urls:
            args.extend(['--urls'] + urls)

    # Model mapping
    model_map = {
        'fast': 'gemini-2.5-flash',
        'balanced': 'gemini-2.5-flash',
        'best': 'gemini-2.5-pro'
    }
    args.extend(['--model', model_map.get(data.get('model', 'fast'), 'gemini-2.5-flash')])

    # Create task
    task_id = str(uuid.uuid4())
    tasks[task_id] = {'status': 'pending', 'created_at': datetime.now().isoformat()}

    # Run async
    run_script_async(
        'get_youtube_news.py',
        args,
        env_vars={'GEMINI_API_KEY': api_key},
        task_id=task_id
    )

    return jsonify({'task_id': task_id})

@app.route('/api/task/<task_id>')
def api_task_status(task_id):
    """Get task status."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(tasks[task_id])

@app.route('/api/extract', methods=['POST'])
def api_extract():
    """Extract links from newsletter."""
    if not CSV_PROCESSOR_AVAILABLE:
        return jsonify({'error': 'CSV processor not available'}), 500

    data = request.json
    mode = data.get('mode', 'url')
    config_name = data.get('config', 'default')
    enrich_grid = data.get('enrichGrid', False)

    # Load config
    custom_instructions = None
    if config_name != 'default':
        config_path = BASE_DIR / 'extraction_instructions' / f'{config_name}.json'
        if config_path.exists():
            custom_instructions = load_custom_instructions(str(config_path))

    # Create processor
    config = ExtractionConfig(
        resolve_redirects=False,
        strip_tracking_params=True
    )
    processor = DataCSVProcessor(config)

    try:
        if mode == 'html':
            html = data.get('html', '')
            source_url = data.get('sourceUrl', '')
            items = processor.process_html(html, source_url, custom_instructions)
        else:
            url = data.get('url', '').strip()
            if not url:
                return jsonify({'error': 'URL required'}), 400
            items = processor.process_url(url, custom_instructions)

        # Optionally enrich with Grid data
        if enrich_grid and items:
            items = processor.enrich_with_grid(items)

        # Convert to JSON
        result_items = []
        for item in items:
            item_dict = {
                'title': item.title,
                'url': item.url,
                'category': item.category,
                'source_name': item.source_name,
                'date_published': item.date_published
            }
            # Add Grid fields if enriched
            if item.custom_fields:
                item_dict.update(item.custom_fields)
            result_items.append(item_dict)

        return jsonify({'items': result_items})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dependencies')
def api_dependencies():
    """Get dependency status."""
    return jsonify(check_dependencies())

@app.route('/api/voices')
def api_voices():
    """Get available voices."""
    voices = voice_manager.get_available_voices()
    return jsonify({'voices': voices})

@app.route('/api/audio/generate', methods=['POST'])
def api_audio_generate():
    """Generate audio from summary."""
    data = request.json
    audio_type = data.get('type', 'fast')
    voice = data.get('voice', 'af_sarah')

    # Create task
    task_id = str(uuid.uuid4())
    tasks[task_id] = {'status': 'pending', 'created_at': datetime.now().isoformat()}

    if audio_type == 'fast':
        script = 'make_audio_fast.py'
        args = []
    else:
        script = 'make_audio_quality.py'
        args = ['--voice', voice]

    run_script_async(script, args, task_id=task_id)

    return jsonify({'task_id': task_id})

@app.route('/api/audio/latest')
def api_audio_latest():
    """Get path to latest audio file."""
    week_folder = BASE_DIR / get_week_folder()

    if week_folder.exists():
        # Look for audio files
        for pattern in ['daily_quality.mp3', 'daily_quality.wav', 'daily_fast.mp3']:
            audio_file = week_folder / pattern
            if audio_file.exists():
                return jsonify({'path': str(audio_file)})

    return jsonify({'path': None})

@app.route('/api/audio/file')
def api_audio_file():
    """Serve audio file."""
    path = request.args.get('path')
    if path and os.path.exists(path):
        return send_file(path)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/settings/apikey', methods=['GET', 'POST'])
def api_settings_apikey():
    """Get/save API key."""
    if request.method == 'POST':
        data = request.json
        file_manager.save_api_key(data.get('key', ''))
        return jsonify({'success': True})
    else:
        key = file_manager.load_api_key()
        return jsonify({'hasKey': bool(key)})

@app.route('/api/settings/instructions', methods=['GET', 'POST'])
def api_settings_instructions():
    """Get/save custom instructions."""
    if request.method == 'POST':
        data = request.json
        save_custom_instructions_text(data.get('instructions', ''))
        return jsonify({'success': True})
    else:
        instructions = load_custom_instructions_text()
        return jsonify({'instructions': instructions})

@app.route('/health')
def health():
    """Health check."""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/manifest.json')
def manifest():
    """PWA manifest."""
    return jsonify({
        'name': 'Daily Audio Briefing',
        'short_name': 'Briefing',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#0f0f0f',
        'theme_color': '#0f0f0f',
        'icons': []
    })

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"\n{'='*50}")
    print("  Daily Audio Briefing - Mobile Web Interface")
    print(f"{'='*50}")
    print(f"\n  Local:   http://localhost:{port}")
    print(f"  Network: http://0.0.0.0:{port}")
    print(f"\n  Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
