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
import gc
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
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

# Import server scheduler
try:
    from server_scheduler import ServerScheduler
    from scheduler import ScheduledTask
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

# Import sheets manager
try:
    from sheets_manager import is_sheets_available
    SHEETS_IMPORT_OK = True
except ImportError:
    SHEETS_IMPORT_OK = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Base directory
BASE_DIR = Path(__file__).parent

# Initialize managers
file_manager = FileManager()
voice_manager = VoiceManager()

# Server mode detection
SERVER_MODE = os.environ.get('SERVER_MODE', 'false').lower() == 'true'

# Task storage (in-memory; use Redis/DB for production)
tasks = {}
TASK_MAX_AGE_SECONDS = 3600  # Evict completed tasks after 1 hour
TASK_MAX_COUNT = 100         # Hard cap regardless of age

def _cleanup_old_tasks():
    """Remove completed/failed tasks older than TASK_MAX_AGE_SECONDS."""
    now = datetime.now()
    to_delete = []
    for tid, tdata in list(tasks.items()):
        if tdata.get('status') not in ('completed', 'failed', 'timeout'):
            continue
        completed_at = tdata.get('completed_at') or tdata.get('created_at')
        if completed_at:
            try:
                age = (now - datetime.fromisoformat(completed_at)).total_seconds()
                if age > TASK_MAX_AGE_SECONDS:
                    to_delete.append(tid)
            except (ValueError, TypeError):
                to_delete.append(tid)
    for tid in to_delete:
        tasks.pop(tid, None)
    # Hard cap: remove oldest completed first
    if len(tasks) > TASK_MAX_COUNT:
        completed = [(tid, tdata) for tid, tdata in tasks.items()
                     if tdata.get('status') in ('completed', 'failed', 'timeout')]
        completed.sort(key=lambda x: x[1].get('created_at', ''))
        for tid, _ in completed[:len(tasks) - TASK_MAX_COUNT]:
            tasks.pop(tid, None)

# Initialize server scheduler (auto-start in server mode)
server_scheduler = None
if SCHEDULER_AVAILABLE:
    server_scheduler = ServerScheduler(data_dir=str(BASE_DIR))
    if SERVER_MODE:
        server_scheduler.start()

# Self-ping keep-alive (prevents Render free tier from sleeping)
def _start_self_ping():
    """Ping own /health endpoint every 4 minutes to prevent Render sleep."""
    import time
    import requests as _requests

    # Detect the public URL from Render's environment
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not render_url:
        print("[keep-alive] No RENDER_EXTERNAL_URL set, self-ping disabled")
        return

    health_url = f"{render_url}/health"
    print(f"[keep-alive] Starting self-ping to {health_url} every 4 minutes")

    def ping_loop():
        while True:
            time.sleep(240)  # 4 minutes

            # Periodic maintenance
            _cleanup_old_tasks()
            gc.collect()

            # Memory watchdog — graceful restart before OOM
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            rss_mb = int(line.split()[1]) / 1024
                            if rss_mb > 480:
                                print(f"[watchdog] EMERGENCY: RSS {rss_mb:.0f}MB > 480MB. Exiting for restart...")
                                os._exit(1)  # gunicorn restarts worker; tasks persist in Sheets
                            elif rss_mb > 450:
                                print(f"[watchdog] WARNING: RSS {rss_mb:.0f}MB > 450MB. Aggressive GC...")
                                gc.collect()
                                gc.collect()
                            break
            except (FileNotFoundError, IOError):
                pass  # Not on Linux (local dev)

            try:
                resp = _requests.get(health_url, timeout=10)
                try:
                    data = resp.json()
                    mem = data.get('memory_current_mb') or data.get('memory_mb', '?')
                    tasks_n = data.get('task_count', '?')
                    print(f"[keep-alive] Ping {resp.status_code} | RSS: {mem}MB | Tasks: {tasks_n}")
                except Exception:
                    print(f"[keep-alive] Ping {resp.status_code}")
            except Exception as e:
                print(f"[keep-alive] Ping failed: {e}")

    t = threading.Thread(target=ping_loop, daemon=True)
    t.start()

if SERVER_MODE:
    _start_self_ping()

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

def list_extraction_configs():
    """List available extraction configs from extraction_instructions/ folder."""
    configs_dir = BASE_DIR / 'extraction_instructions'
    configs = []
    if configs_dir.exists():
        for f in sorted(configs_dir.glob('*.json')):
            if f.stem.startswith('_'):
                continue  # Skip _template.json
            try:
                data = json.loads(f.read_text())
                configs.append({
                    'name': f.stem,
                    'display_name': data.get('name', f.stem),
                    'description': data.get('description', ''),
                    'csv_columns': data.get('csv_columns', []),
                })
            except:
                configs.append({'name': f.stem, 'display_name': f.stem, 'csv_columns': []})
    return configs


def get_extraction_config(name):
    """Get a single extraction config by name."""
    config_path = BASE_DIR / 'extraction_instructions' / f'{name}.json'
    if config_path.exists():
        return json.loads(config_path.read_text())
    return None


def check_dependencies():
    """Check available dependencies on this server/machine."""
    deps = {
        'ffmpeg': False,
        'faster_whisper': False,
        'kokoro': False,
        'gtts': False,
        'server_mode': SERVER_MODE
    }

    # Check ffmpeg (system tool — needed for audio file processing)
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        deps['ffmpeg'] = True
    except:
        pass

    # Check gTTS (lightweight Google TTS — works on any server)
    try:
        import gtts
        deps['gtts'] = True
    except:
        pass

    # Check faster-whisper (heavy AI model — needs 1GB+ RAM)
    try:
        import faster_whisper
        deps['faster_whisper'] = True
    except:
        pass

    # Check kokoro (ONNX model file — ~300MB + runtime RAM)
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
            del stdout, stderr  # Free subprocess buffers before GC

        except subprocess.TimeoutExpired:
            tasks[task_id]['status'] = 'timeout'
            tasks[task_id]['error'] = 'Task timed out after 1 hour'
        except Exception as e:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = str(e)
        finally:
            gc.collect()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    return thread

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

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

        # Convert to JSON - include all fields matching sheet columns
        result_items = []
        for item in items:
            item_dict = {
                'title': item.title,
                'url': item.url,
                'source_name': item.source_name,
                'category': item.category,
                'description': item.description,
                'author': item.author,
                'date_published': item.date_published,
                'date_extracted': item.date_extracted
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
    """Get dependency status (checks what's installed on this server/machine)."""
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

# =============================================================================
# SCHEDULER API ROUTES
# =============================================================================

@app.route('/api/scheduler/status')
def api_scheduler_status():
    """Get scheduler status."""
    if not server_scheduler:
        return jsonify({'available': False, 'running': False})
    return jsonify({
        'available': True,
        'running': server_scheduler.is_running,
        'task_count': len(server_scheduler.tasks),
        'sheets_available': SHEETS_IMPORT_OK and is_sheets_available() if SHEETS_IMPORT_OK else False,
    })


@app.route('/api/scheduler/toggle', methods=['POST'])
def api_scheduler_toggle():
    """Start or stop the scheduler."""
    if not server_scheduler:
        return jsonify({'error': 'Scheduler not available'}), 500
    data = request.json or {}
    if data.get('running', True):
        server_scheduler.start()
    else:
        server_scheduler.stop()
    return jsonify({'running': server_scheduler.is_running})


@app.route('/api/scheduler/tasks', methods=['GET'])
def api_scheduler_tasks_list():
    """List all scheduled tasks."""
    if not server_scheduler:
        return jsonify({'tasks': []})
    # If background thread hasn't loaded tasks yet, load them on-demand
    if not server_scheduler.scheduler._tasks_loaded:
        server_scheduler.scheduler.load_tasks()
        server_scheduler.scheduler._tasks_loaded = True
    return jsonify({
        'tasks': [t.to_dict() for t in server_scheduler.tasks]
    })


@app.route('/api/scheduler/tasks', methods=['POST'])
def api_scheduler_tasks_create():
    """Create a new scheduled task."""
    if not server_scheduler:
        return jsonify({'error': 'Scheduler not available'}), 500

    data = request.json
    task = ScheduledTask(
        id='',  # Will be auto-generated
        name=data.get('name', 'New Task'),
        enabled=data.get('enabled', True),
        source_url=data.get('source_url', ''),
        config_name=data.get('config_name', 'Default'),
        interval=data.get('interval', 'daily'),
        custom_hours=data.get('custom_hours', 24),
        run_at_time=data.get('run_at_time', '09:00'),
        run_on_day=data.get('run_on_day', 0),
        export_to_sheets=data.get('export_to_sheets', False),
        spreadsheet_id=data.get('spreadsheet_id', ''),
        sheet_name=data.get('sheet_name', 'Sheet1'),
        include_headers=data.get('include_headers', False),
        custom_columns=data.get('custom_columns'),
    )
    server_scheduler.add_task(task)
    return jsonify({'success': True, 'task': task.to_dict()})


@app.route('/api/scheduler/tasks/<task_id>', methods=['PUT'])
def api_scheduler_tasks_update(task_id):
    """Update an existing task."""
    if not server_scheduler:
        return jsonify({'error': 'Scheduler not available'}), 500

    data = request.json
    success = server_scheduler.update_task(task_id, data)
    if success:
        task = server_scheduler.get_task(task_id)
        return jsonify({'success': True, 'task': task.to_dict() if task else {}})
    return jsonify({'error': 'Task not found'}), 404


@app.route('/api/scheduler/tasks/<task_id>', methods=['DELETE'])
def api_scheduler_tasks_delete(task_id):
    """Delete a task."""
    if not server_scheduler:
        return jsonify({'error': 'Scheduler not available'}), 500

    success = server_scheduler.delete_task(task_id)
    return jsonify({'success': success})


@app.route('/api/scheduler/tasks/<task_id>/run', methods=['POST'])
def api_scheduler_tasks_run(task_id):
    """Run a task immediately."""
    if not server_scheduler:
        return jsonify({'error': 'Scheduler not available'}), 500

    success = server_scheduler.run_task_now(task_id)
    return jsonify({'success': success})


# =============================================================================
# EXTRACTION CONFIG API ROUTES
# =============================================================================

@app.route('/api/configs')
def api_configs_list():
    """List extraction configs."""
    return jsonify({'configs': list_extraction_configs()})


@app.route('/api/configs/<name>')
def api_configs_get(name):
    """Get a single extraction config."""
    config = get_extraction_config(name)
    if config:
        return jsonify(config)
    return jsonify({'error': 'Config not found'}), 404


@app.route('/api/configs/<name>', methods=['PUT'])
def api_configs_update(name):
    """Update an extraction config (e.g., csv_columns)."""
    config_path = BASE_DIR / 'extraction_instructions' / f'{name}.json'
    if not config_path.exists():
        return jsonify({'error': 'Config not found'}), 404

    existing = json.loads(config_path.read_text())
    updates = request.json
    # Only allow updating safe fields
    safe_fields = (
        'csv_columns', 'include_patterns', 'exclude_patterns',
        'blocked_domains', 'allowed_domains', 'source_url_patterns',
        'description', 'output_format'
    )
    for key in safe_fields:
        if key in updates:
            existing[key] = updates[key]
    config_path.write_text(json.dumps(existing, indent=2))
    return jsonify({'success': True})


# =============================================================================
# SHEETS PREVIEW API
# =============================================================================

@app.route('/api/sheets/preview', methods=['POST'])
def api_sheets_preview():
    """Preview what the Sheet output will look like for a given config + optional column overrides."""
    data = request.json
    config_name = data.get('config_name', '')
    custom_columns = data.get('custom_columns')

    # Determine columns
    columns = custom_columns
    if not columns and config_name and config_name != 'Default':
        config = get_extraction_config(config_name.lower().replace(' ', '_'))
        if config:
            columns = config.get('csv_columns', [])

    if not columns:
        columns = ['title', 'url', 'date_published', 'source_name', 'description']

    # Generate mock rows with realistic sample data
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    mock_rows = [
        {
            'title': 'BlackRock Tokenized Fund Surpasses $500M',
            'url': 'https://example.com/blackrock-fund',
            'date_published': today,
            'date_extracted': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'source_name': 'RWAxyz',
            'section': 'News',
            'description': 'BlackRock\'s tokenized money market fund BUIDL crosses $500M in AUM.',
            'author': 'Staff Writer',
            'original_url': 'https://example.com/blackrock-fund',
            'Track?': '',
        },
        {
            'title': 'Ondo Finance Launches New RWA Vault',
            'url': 'https://example.com/ondo-vault',
            'date_published': today,
            'date_extracted': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'source_name': 'CoinDesk',
            'section': 'DeFi',
            'description': 'Ondo Finance introduces tokenized US Treasuries vault with instant redemption.',
            'author': 'DeFi Desk',
            'original_url': 'https://example.com/ondo-vault',
            'Track?': '',
        },
        {
            'title': 'Securitize Partners with Hamilton Lane',
            'url': 'https://example.com/securitize-hamilton',
            'date_published': yesterday,
            'date_extracted': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'source_name': 'The Block',
            'section': 'Institutional',
            'description': 'Securitize brings Hamilton Lane private equity funds on-chain.',
            'author': 'Institutional Reporter',
            'original_url': 'https://example.com/securitize-hamilton',
            'Track?': '',
        },
    ]

    rows = []
    for mock in mock_rows:
        rows.append([mock.get(col, '') for col in columns])

    return jsonify({'columns': columns, 'rows': rows})


@app.route('/api/sheets/deduplicate', methods=['POST'])
def api_sheets_deduplicate():
    """Deduplicate an existing Google Sheet by removing duplicate URLs."""
    data = request.json
    spreadsheet_id = data.get('spreadsheet_id', '')
    sheet_name = data.get('sheet_name', 'Sheet1')
    dedup_column = data.get('dedup_column', 'url')

    if not spreadsheet_id:
        return jsonify({'error': 'spreadsheet_id required'}), 400

    try:
        from sheets_manager import deduplicate_sheet, extract_sheet_id, is_sheets_available
        if not is_sheets_available():
            return jsonify({'error': 'Google Sheets not configured'}), 400

        sid = extract_sheet_id(spreadsheet_id)
        result = deduplicate_sheet(sid, sheet_name, dedup_column)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sheets/validate-tab', methods=['POST'])
def api_sheets_validate_tab():
    """Check if a sheet tab exists. Returns existing tabs and match status."""
    data = request.json
    spreadsheet_id = data.get('spreadsheet_id', '')
    tab_name = data.get('tab_name', '')

    if not spreadsheet_id or not tab_name:
        return jsonify({'error': 'spreadsheet_id and tab_name required'}), 400

    try:
        from sheets_manager import (
            get_sheet_tab_names, extract_sheet_id, is_sheets_available
        )
        if not is_sheets_available():
            return jsonify({'error': 'Google Sheets not configured'}), 400

        sid = extract_sheet_id(spreadsheet_id)
        tabs = get_sheet_tab_names(sid)
        exists = tab_name in tabs

        return jsonify({
            'exists': exists,
            'tab_name': tab_name,
            'available_tabs': tabs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sheets/create-tab', methods=['POST'])
def api_sheets_create_tab():
    """Create a new tab in a Google Spreadsheet."""
    data = request.json
    spreadsheet_id = data.get('spreadsheet_id', '')
    tab_name = data.get('tab_name', '')

    if not spreadsheet_id or not tab_name:
        return jsonify({'error': 'spreadsheet_id and tab_name required'}), 400

    try:
        from sheets_manager import (
            create_sheet_tab, extract_sheet_id, is_sheets_available
        )
        if not is_sheets_available():
            return jsonify({'error': 'Google Sheets not configured'}), 400

        sid = extract_sheet_id(spreadsheet_id)
        success = create_sheet_tab(sid, tab_name)

        if success:
            return jsonify({'created': True, 'tab_name': tab_name})
        else:
            return jsonify({'error': f'Failed to create tab: {tab_name}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check with memory stats (useful for diagnosing OOM on 512MB Render)."""
    import resource
    import platform

    # Peak RSS (high-water mark — only goes up)
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == 'Linux':
        peak_mb = peak_rss / 1024  # Linux: KB -> MB
    else:
        peak_mb = peak_rss / (1024 * 1024)  # macOS: bytes -> MB

    # Current RSS from /proc (Linux only — actual current usage)
    current_mb = None
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    current_mb = int(line.split()[1]) / 1024  # KB -> MB
                    break
    except (FileNotFoundError, IOError):
        pass  # Not on Linux (local dev)

    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'scheduler_running': server_scheduler.is_running if server_scheduler else False,
        'memory_mb': round(current_mb, 1) if current_mb is not None else round(peak_mb, 1),
        'memory_current_mb': round(current_mb, 1) if current_mb is not None else None,
        'memory_peak_mb': round(peak_mb, 1),
        'task_count': len(tasks),
    })

@app.route('/favicon.ico')
def favicon_ico():
    """Serve favicon.ico — browsers always request this."""
    import base64
    ICO_B64 = "AAABAAEAEBAAAAAAIADnAAAAFgAAAIlQTkcNChoKAAAADUlIRFIAAAAQAAAAEAgGAAAAH/P/YQAAAK5JREFUeJxjYKAQMCJzhESk/hOj6d2bZ3B9TKRqRlfLiCzAJyxLlAGf3j6Gu4SJgFqCgGIDWJA5m9YvxVCQlVeJwt+5aTGDrJwSdgOwgZ2bFhPvAmzA3S+WMgOQXWC/6DHDwThZFC+gRKOWgTUh8xgYGBgYrl04ysDAAIlGFBfg8q/9oseoAhfs4UwUA3D5lwOPa+BpmpSkzMCAyA8omcnGJZQoQ47sWc1IWBWRAADPHTCqNjkNHwAAAABJRU5ErkJggg=="
    data = base64.b64decode(ICO_B64)
    return Response(data, mimetype='image/x-icon',
                    headers={'Cache-Control': 'public, max-age=604800'})


@app.route('/favicon-32.png')
def favicon_32():
    """Serve 32x32 PNG favicon."""
    import base64
    PNG32_B64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABTklEQVR4nGNgGOmAEZeEkIjUf2pa9O7NM6x2MdHDcnxmYjiAFpbjM5uJkAJaO4IJlwS9HMFCjIbHj+6RZZGsnBJBNfCUiSsE+IRlybIcBj69fYxVHJYrsOYCGCDX56SYgdcB9ACjDiCYC66ePziwDmBgYGC4++AJTjllBRkGBgYGBne/WAy5nZsWEzQbbzZ8/OgeXsvRHYELYCsPYNmQqBAgBmALAQYGwqFANQcgW2S/6DHDwTjiCjCqh8CPkDYUPl1DwH4Rotj9EdJGVCgQLAcIJTCYPLLlMIBNDB0QFQKEHIHPIkKOIOgAXKkbGXDgkdu5aTGDbA2ZDpCVUyK5RoT5GBb/hNoEVAkBZAALDfc1xKkn2CChFYCVhChtdWyO0DKwpsiiaxeO4rQcwwG4HEFNgN5BwdpbQXZEaSGAzce4LMfpAHRHUAPg6pqNAgBtCXK0fWb/cgAAAABJRU5ErkJggg=="
    data = base64.b64decode(PNG32_B64)
    return Response(data, mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=604800'})


@app.route('/favicon-apple.png')
def favicon_apple():
    """Serve Apple touch icon (180x180)."""
    import base64
    APPLE_B64 = "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"
    data = base64.b64decode(APPLE_B64)
    return Response(data, mimetype='image/png',
                    headers={'Cache-Control': 'public, max-age=604800'})


@app.route('/manifest.json')
def manifest():
    """PWA manifest with icons."""
    return jsonify({
        'name': 'Daily Audio Briefing',
        'short_name': 'Briefing',
        'start_url': '/',
        'display': 'standalone',
        'background_color': '#0f0f0f',
        'theme_color': '#0f0f0f',
        'icons': [
            {'src': '/favicon-32.png', 'sizes': '32x32', 'type': 'image/png'},
            {'src': '/favicon-apple.png', 'sizes': '180x180', 'type': 'image/png'}
        ]
    })

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"\n{'='*50}")
    print("  Daily Audio Briefing - Mobile Web Interface")
    print(f"{'='*50}")
    print(f"\n  Local:   http://localhost:{port}")
    print(f"  Network: http://0.0.0.0:{port}")
    print(f"\n  Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
