"""
Scheduler Module - Background extraction and export automation

This module provides:
1. Scheduled task management (create, edit, delete, enable/disable)
2. Background thread that runs tasks at configured intervals
3. Auto-extraction from configured sources
4. Auto-export to Google Sheets
"""

import gc
import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class ScheduleInterval(Enum):
    """Supported scheduling intervals."""
    HOURLY = "hourly"
    EVERY_6_HOURS = "every_6_hours"
    EVERY_12_HOURS = "every_12_hours"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM_HOURS = "custom_hours"


@dataclass
class ScheduledTask:
    """A scheduled extraction task."""
    id: str
    name: str
    enabled: bool = True

    # Source configuration
    source_url: str = ""  # URL to extract from (Telegram, newsletter, etc.)
    config_name: str = "Default"  # Extraction config to use

    # Schedule settings
    interval: str = "daily"  # ScheduleInterval value
    custom_hours: int = 24  # For custom_hours interval
    run_at_time: str = "09:00"  # Time to run (HH:MM format) for daily/weekly
    run_on_day: int = 0  # Day of week (0=Monday) for weekly

    # Export settings
    export_to_sheets: bool = False
    spreadsheet_id: str = ""
    sheet_name: str = "Sheet1"
    include_headers: bool = False  # Only include headers on first export
    custom_columns: Optional[List[str]] = None  # Per-task column override (None = use config default)

    # Capabilities (optional enrichment steps during task execution)
    enrich_with_grid: bool = False  # Run Grid entity matching after extraction
    research_articles: bool = False  # Run article research for ecosystem mentions

    # Pipeline settings (only used when task_type == "briefing_pipeline")
    task_type: str = "extraction"  # "extraction" or "briefing_pipeline"
    audio_quality: str = "quality"  # "fast" (gTTS) or "quality" (Kokoro)
    audio_voice: str = "af_heart"  # Kokoro voice name
    upload_to_drive: bool = False
    drive_folder_id: str = ""
    source_filter: Optional[List[str]] = None  # None = all enabled sources

    # Runtime state (not persisted)
    last_run: Optional[str] = None  # ISO format datetime
    next_run: Optional[str] = None  # ISO format datetime
    last_result: str = ""  # Success/error message
    items_extracted: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "source_url": self.source_url,
            "config_name": self.config_name,
            "interval": self.interval,
            "custom_hours": self.custom_hours,
            "run_at_time": self.run_at_time,
            "run_on_day": self.run_on_day,
            "export_to_sheets": self.export_to_sheets,
            "spreadsheet_id": self.spreadsheet_id,
            "sheet_name": self.sheet_name,
            "include_headers": self.include_headers,
            "custom_columns": self.custom_columns,
            "enrich_with_grid": self.enrich_with_grid,
            "research_articles": self.research_articles,
            "task_type": self.task_type,
            "audio_quality": self.audio_quality,
            "audio_voice": self.audio_voice,
            "upload_to_drive": self.upload_to_drive,
            "drive_folder_id": self.drive_folder_id,
            "source_filter": self.source_filter,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "last_result": self.last_result,
            "items_extracted": self.items_extracted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScheduledTask':
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Untitled Task"),
            enabled=data.get("enabled", True),
            source_url=data.get("source_url", ""),
            config_name=data.get("config_name", "Default"),
            interval=data.get("interval", "daily"),
            custom_hours=data.get("custom_hours", 24),
            run_at_time=data.get("run_at_time", "09:00"),
            run_on_day=data.get("run_on_day", 0),
            export_to_sheets=data.get("export_to_sheets", False),
            spreadsheet_id=data.get("spreadsheet_id", ""),
            sheet_name=data.get("sheet_name", "Sheet1"),
            include_headers=data.get("include_headers", False),
            custom_columns=data.get("custom_columns"),
            enrich_with_grid=data.get("enrich_with_grid", False),
            research_articles=data.get("research_articles", False),
            task_type=data.get("task_type", "extraction"),
            audio_quality=data.get("audio_quality", "quality"),
            audio_voice=data.get("audio_voice", "af_heart"),
            upload_to_drive=data.get("upload_to_drive", False),
            drive_folder_id=data.get("drive_folder_id", ""),
            source_filter=data.get("source_filter"),
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            last_result=data.get("last_result", ""),
            items_extracted=data.get("items_extracted", 0),
        )


def get_scheduler_config_path(data_dir: Optional[str] = None) -> str:
    """Get path to scheduler configuration file.

    Args:
        data_dir: Override data directory (used in server mode).
                  If None, uses frozen app or development mode paths.
    """
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "scheduled_tasks.json")
    elif getattr(sys, 'frozen', False):
        # Running as frozen app
        if sys.platform == 'darwin':
            app_support = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
        elif sys.platform == 'win32':
            app_support = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
        else:
            app_support = os.path.expanduser("~/.daily-audio-briefing")
        os.makedirs(app_support, exist_ok=True)
        return os.path.join(app_support, "scheduled_tasks.json")
    else:
        # Development mode
        return os.path.join(os.path.dirname(__file__), "scheduled_tasks.json")


class Scheduler:
    """Background scheduler for automated extraction tasks."""

    def __init__(self, on_task_complete: Optional[Callable] = None,
                 on_progress: Optional[Callable] = None,
                 server_mode: bool = False, data_dir: Optional[str] = None):
        """
        Initialize the scheduler.

        Args:
            on_task_complete: Callback function(task, success, message) called after each task runs
            on_progress: Callback function(task_id, message) called with progress log lines during execution
            server_mode: If True, log to stdout and skip OS-level daemon operations
            data_dir: Override data directory for config/task files (used in server mode)
        """
        self.tasks: List[ScheduledTask] = []
        self.running = False
        self.server_mode = server_mode
        self.data_dir = data_dir
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_task_complete = on_task_complete
        self._on_progress = on_progress
        self._lock = threading.Lock()
        self._running_tasks: set = set()  # Per-task mutex: track running task IDs
        self._tasks_loaded = False

        # In server mode, defer load_tasks() to the background thread so
        # Sheets API calls don't block gunicorn worker boot (120s timeout).
        if not server_mode:
            self.load_tasks()
            self._tasks_loaded = True

    def load_tasks(self):
        """Load scheduled tasks with multi-tier fallback.

        Priority:
        1. Config file on disk (always preferred if it exists)
        2. Google Sheets _scheduler_config tab (survives Render redeploys)
        3. SCHEDULED_TASKS_JSON env var (initial seed / emergency fallback)
        """
        config_path = get_scheduler_config_path(self.data_dir)
        loaded_from = None

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]
                    loaded_from = "file"
            except Exception as e:
                print(f"[Scheduler] Error loading tasks from file: {e}")
                self.tasks = []

        # Fallback 1: Google Sheets persistence (server mode)
        if not self.tasks and self.server_mode:
            sheet_data = self._load_from_sheets()
            if sheet_data:
                try:
                    self.tasks = [ScheduledTask.from_dict(t) for t in sheet_data.get("tasks", [])]
                    loaded_from = "sheets"
                    self._write_tasks_to_file(config_path)
                except Exception as e:
                    print(f"[Scheduler] Error parsing tasks from Sheets: {e}")
                    self.tasks = []

        # Fallback 2: env var (initial seed / emergency)
        if not self.tasks:
            env_tasks = os.environ.get('SCHEDULED_TASKS_JSON')
            if env_tasks:
                try:
                    data = json.loads(env_tasks)
                    self.tasks = [ScheduledTask.from_dict(t) for t in data.get("tasks", [])]
                    loaded_from = "env:SCHEDULED_TASKS_JSON"
                    self._write_tasks_to_file(config_path)
                except Exception as e:
                    print(f"[Scheduler] Error loading tasks from env var: {e}")
                    self.tasks = []

        # Recalculate next run times
        for task in self.tasks:
            if task.enabled:
                task.next_run = self._calculate_next_run(task)

        if loaded_from and self.tasks:
            print(f"[Scheduler] Loaded {len(self.tasks)} task(s) from {loaded_from}")

    def _write_tasks_to_file(self, config_path: str):
        """Write tasks to file (internal helper)."""
        try:
            data = {"tasks": [t.to_dict() for t in self.tasks]}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Scheduler] Error writing tasks to file: {e}")

    def save_tasks(self):
        """Save scheduled tasks to config file and (in server mode) to Google Sheets."""
        config_path = get_scheduler_config_path(self.data_dir)
        data = {"tasks": [t.to_dict() for t in self.tasks]}

        self._write_tasks_to_file(config_path)

        # In server mode, persist to Google Sheets (survives redeploys)
        if self.server_mode:
            self._save_to_sheets(data)

    # --- Google Sheets persistence helpers ---

    def _get_persistence_sheet_id(self) -> Optional[str]:
        """Get the spreadsheet ID used for config persistence."""
        return os.environ.get('SCHEDULER_SHEET_ID')

    def _save_to_sheets(self, data: dict):
        """Write tasks JSON to the _scheduler_config tab of the persistence sheet."""
        sheet_id = self._get_persistence_sheet_id()
        if not sheet_id:
            return

        try:
            from sheets_manager import is_sheets_available, get_sheets_service
            if not is_sheets_available():
                return

            service = get_sheets_service()
            json_str = json.dumps(data, indent=2)

            # Ensure the _scheduler_config tab exists
            try:
                service.spreadsheets().values().get(
                    spreadsheetId=sheet_id,
                    range='_scheduler_config!A1'
                ).execute()
            except Exception:
                # Tab doesn't exist — create it
                try:
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body={'requests': [{'addSheet': {'properties': {'title': '_scheduler_config'}}}]}
                    ).execute()
                except Exception:
                    pass  # Tab might already exist in a race

            # Write JSON to cell A1
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='_scheduler_config!A1',
                valueInputOption='RAW',
                body={'values': [[json_str]]}
            ).execute()
            print(f"[Scheduler] Saved {len(data.get('tasks', []))} task(s) to Sheets persistence")
        except Exception as e:
            print(f"[Scheduler] Warning: Could not save to Sheets: {e}")

    def _load_from_sheets(self) -> Optional[dict]:
        """Read tasks JSON from the _scheduler_config tab of the persistence sheet."""
        sheet_id = self._get_persistence_sheet_id()
        if not sheet_id:
            return None

        try:
            from sheets_manager import is_sheets_available, get_sheets_service
            if not is_sheets_available():
                return None

            service = get_sheets_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='_scheduler_config!A1'
            ).execute()
            values = result.get('values', [])
            if values and values[0]:
                data = json.loads(values[0][0])
                print(f"[Scheduler] Read config from Sheets persistence")
                return data
        except Exception as e:
            print(f"[Scheduler] Could not load from Sheets: {e}")
        return None

    def add_task(self, task: ScheduledTask) -> bool:
        """Add a new scheduled task."""
        with self._lock:
            # Generate unique ID if not set
            if not task.id:
                task.id = f"task_{int(time.time() * 1000)}"

            # Calculate next run time
            if task.enabled:
                task.next_run = self._calculate_next_run(task)

            self.tasks.append(task)
            self.save_tasks()
            return True

    def update_task(self, task_id: str, updates: dict) -> bool:
        """Update an existing task."""
        with self._lock:
            for task in self.tasks:
                if task.id == task_id:
                    for key, value in updates.items():
                        if hasattr(task, key):
                            setattr(task, key, value)
                    # Recalculate next run if schedule changed
                    if task.enabled:
                        task.next_run = self._calculate_next_run(task)
                    self.save_tasks()
                    return True
            return False

    def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        with self._lock:
            for i, task in enumerate(self.tasks):
                if task.id == task_id:
                    del self.tasks[i]
                    self.save_tasks()
                    return True
            return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def _calculate_next_run(self, task: ScheduledTask) -> str:
        """Calculate the next run time for a task."""
        now = datetime.now()

        if task.interval == "hourly":
            # Next hour, at the start
            next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        elif task.interval == "every_6_hours":
            # Find next 6-hour mark (0, 6, 12, 18)
            current_hour = now.hour
            next_hour = ((current_hour // 6) + 1) * 6
            if next_hour >= 24:
                next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_run = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)

        elif task.interval == "every_12_hours":
            # Find next 12-hour mark (0, 12)
            current_hour = now.hour
            if current_hour < 12:
                next_run = now.replace(hour=12, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        elif task.interval == "daily":
            # Run at specified time
            try:
                hour, minute = map(int, task.run_at_time.split(":"))
            except:
                hour, minute = 9, 0
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)

        elif task.interval == "weekly":
            # Run on specified day at specified time
            try:
                hour, minute = map(int, task.run_at_time.split(":"))
            except:
                hour, minute = 9, 0
            days_ahead = task.run_on_day - now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and now.hour * 60 + now.minute >= hour * 60 + minute):
                days_ahead += 7
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)

        elif task.interval == "custom_hours":
            # Run every N hours from now
            next_run = now + timedelta(hours=task.custom_hours)

        else:
            # Default to daily
            next_run = now + timedelta(days=1)

        return next_run.isoformat()

    def start(self):
        """Start the background scheduler thread."""
        if self.running:
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Scheduler] Started")

    def stop(self):
        """Stop the background scheduler thread."""
        if not self.running:
            return

        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[Scheduler] Stopped")

    def _run_loop(self):
        """Main scheduler loop - checks for tasks to run."""
        # In server mode, load tasks here (background thread) instead of __init__
        # to avoid blocking gunicorn worker boot with slow Sheets API calls.
        if not self._tasks_loaded:
            try:
                self.load_tasks()
                self._tasks_loaded = True
            except Exception as e:
                print(f"[Scheduler] Error loading tasks in background: {e}")

        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                # Collect tasks due to run (under lock), then execute outside lock
                tasks_to_run = []
                with self._lock:
                    for task in self.tasks:
                        if not task.enabled or not task.next_run:
                            continue
                        try:
                            next_run = datetime.fromisoformat(task.next_run)
                            if now >= next_run:
                                tasks_to_run.append(task)
                        except Exception as e:
                            print(f"[Scheduler] Error checking task {task.name}: {e}")

                # Execute outside lock so other operations aren't blocked
                for task in tasks_to_run:
                    if self._stop_event.is_set():
                        break
                    self._execute_task(task)

                # Check every 30 seconds
                self._stop_event.wait(30)

            except Exception as e:
                print(f"[Scheduler] Error in run loop: {e}")
                self._stop_event.wait(60)

    def _log(self, task_id: str, message: str):
        """Print and optionally forward progress to the GUI callback."""
        print(message)
        if self._on_progress:
            try:
                self._on_progress(task_id, message)
            except Exception:
                pass

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task. Guarded by mutex to prevent concurrent runs."""
        # Per-task mutex: skip if THIS task is already running
        if task.id in self._running_tasks:
            print(f"[Scheduler] Skipping '{task.name}' — already running")
            return
        self._running_tasks.add(task.id)

        # Set task context for API usage attribution
        from api_usage_tracker import set_current_task, clear_current_task
        set_current_task(task.id, task.name)

        self._log(task.id, f"[Scheduler] Running task: {task.name}")
        task.last_run = datetime.now().isoformat()

        try:
            # Route to pipeline executor for briefing tasks
            if task.task_type == "briefing_pipeline":
                self._execute_pipeline_task(task)

                # Calculate next run and save
                task.next_run = self._calculate_next_run(task)
                self.save_tasks()

                if self._on_task_complete:
                    is_success = not task.last_result.startswith("Error")
                    self._on_task_complete(task, is_success, task.last_result)
                return

            # Import here to avoid circular imports
            from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions

            # Create processor — use lean config in server mode (512MB limit)
            config = ExtractionConfig()
            if self.server_mode:
                config.max_workers = 2
                config.resolve_redirects = False
            processor = DataCSVProcessor(config)

            # Load custom instructions if not default
            custom_instructions = None
            if task.config_name != "Default":
                config_file = task.config_name.lower().replace(" ", "_") + ".json"
                config_path = os.path.join(os.path.dirname(__file__), "extraction_instructions", config_file)
                if os.path.exists(config_path):
                    custom_instructions = load_custom_instructions(config_path)
                    self._log(task.id, f"[Scheduler] Loaded config: {task.config_name}")

            # Normalize URL - ensure it has a scheme
            source_url = task.source_url.strip()
            if source_url and not source_url.startswith(('http://', 'https://')):
                source_url = 'https://' + source_url

            self._log(task.id, f"[Scheduler] Fetching: {source_url[:80]}...")

            # Extract items
            items = processor.process_url(source_url, custom_instructions)
            task.items_extracted = len(items)
            self._log(task.id, f"[Scheduler] Extracted {len(items)} items")

            # Enrich with Grid entity matching (if enabled)
            if task.enrich_with_grid and items:
                try:
                    self._log(task.id, f"[Scheduler] Enriching {len(items)} items with Grid data...")
                    items = processor.enrich_with_grid(items)
                    matched = sum(1 for i in items if i.custom_fields.get('grid_matched'))
                    self._log(task.id, f"[Scheduler] Grid enrichment: {matched}/{len(items)} items matched")
                except Exception as e:
                    self._log(task.id, f"[Scheduler] Grid enrichment error (continuing): {e}")

            # Research articles for ecosystem mentions (if enabled)
            if task.research_articles and items:
                try:
                    self._log(task.id, f"[Scheduler] Researching articles for {len(items)} items...")
                    items = processor.research_articles(items, all_items=True)
                    self._log(task.id, f"[Scheduler] Article research complete")
                except Exception as e:
                    self._log(task.id, f"[Scheduler] Article research error (continuing): {e}")

            # Export to Google Sheets if enabled
            if task.export_to_sheets and items and task.spreadsheet_id:
                try:
                    from sheets_manager import (
                        export_items_to_sheet, is_sheets_available, resolve_sheet_name,
                        deduplicate_sheet, sort_sheet_by_date
                    )

                    if is_sheets_available():
                        self._log(task.id, f"[Scheduler] Exporting to Google Sheets...")
                        # Auto-detect renamed sheet tabs
                        resolved_name = resolve_sheet_name(task.spreadsheet_id, task.sheet_name)
                        if resolved_name and resolved_name != task.sheet_name:
                            self._log(task.id, f"[Scheduler] Sheet tab renamed: '{task.sheet_name}' → '{resolved_name}'")
                            task.sheet_name = resolved_name

                        if not resolved_name:
                            task.last_result = (
                                f"Extracted {len(items)} items, "
                                f"Sheets error: tab '{task.sheet_name}' not found"
                            )
                        else:
                            # Get columns: task override > config default
                            columns = task.custom_columns
                            if not columns and custom_instructions:
                                columns = custom_instructions.get('csv_columns')

                            result = export_items_to_sheet(
                                items=items,
                                spreadsheet_id=task.spreadsheet_id,
                                sheet_name=task.sheet_name,
                                columns=columns,
                                include_headers=task.include_headers
                            )

                            updated = result.get('updates', {}).get('updatedRows', len(items))
                            task.last_result = f"Success: {len(items)} items → {updated} rows to Sheets"
                            self._log(task.id, f"[Scheduler] {task.last_result}")

                            # Auto-deduplicate and sort the sheet after each export
                            try:
                                dedup_result = deduplicate_sheet(
                                    task.spreadsheet_id, task.sheet_name
                                )
                                removed = dedup_result.get('removed_count', 0) if isinstance(dedup_result, dict) else 0
                                if removed > 0:
                                    self._log(task.id, f"[Scheduler] Cleaned {removed} duplicate/empty rows")
                                sort_sheet_by_date(
                                    task.spreadsheet_id, task.sheet_name
                                )
                            except Exception as dedup_err:
                                self._log(task.id, f"[Scheduler] Dedup/sort warning: {dedup_err}")
                    else:
                        task.last_result = f"Extracted {len(items)} items (Sheets not configured)"
                        self._log(task.id, f"[Scheduler] {task.last_result}")
                except Exception as e:
                    task.last_result = f"Extracted {len(items)} items, Sheets error: {str(e)[:50]}"
                    self._log(task.id, f"[Scheduler] {task.last_result}")
            else:
                task.last_result = f"Success: Extracted {len(items)} items"
                self._log(task.id, f"[Scheduler] {task.last_result}")

            # Calculate next run
            task.next_run = self._calculate_next_run(task)
            self.save_tasks()

            # Callback
            if self._on_task_complete:
                self._on_task_complete(task, True, task.last_result)

        except Exception as e:
            task.last_result = f"Error: {str(e)[:100]}"
            task.next_run = self._calculate_next_run(task)
            self.save_tasks()

            if self._on_task_complete:
                self._on_task_complete(task, False, task.last_result)

            self._log(task.id, f"[Scheduler] Task failed: {e}")

        finally:
            clear_current_task()
            self._running_tasks.discard(task.id)
            # Force garbage collection after task to reclaim memory (512MB limit)
            gc.collect()

    def _execute_pipeline_task(self, task: ScheduledTask):
        """Execute a briefing pipeline task: fetch → summarize → audio → Drive.

        Steps:
            1. Load and filter sources from sources.json
            2. Fetch + AI-summarize via SourceFetcher
            3. Format text for audio narration
            4. Save summary text to Week_N_YYYY folder
            5. Generate audio via TTS subprocess (skip in server mode)
            6. Upload audio to Google Drive (if configured)
        """
        from source_fetcher import load_sources, SourceFetcher, format_items_for_audio
        from file_manager import FileManager

        fm = FileManager()
        api_key = fm.load_api_key() or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            task.last_result = "Error: No Gemini API key configured"
            self._log(task.id, f"[Pipeline] {task.last_result}")
            return

        # --- Step 1: Load and filter sources ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = fm.base_dir
        sources_json = os.path.join(data_dir, "sources.json")
        channels_txt = os.path.join(data_dir, "channels.txt")

        # Fall back to bundled files if user files don't exist
        if not os.path.exists(sources_json):
            sources_json = os.path.join(script_dir, "sources.json")
            if getattr(sys, "frozen", False):
                sources_json = os.path.join(sys._MEIPASS, "sources.json")
        if not os.path.exists(channels_txt):
            channels_txt = os.path.join(script_dir, "channels.txt")
            if getattr(sys, "frozen", False):
                channels_txt = os.path.join(sys._MEIPASS, "channels.txt")

        sources = load_sources(sources_json, channels_txt)

        if task.source_filter:
            sources = [s for s in sources if s.name in task.source_filter]

        enabled = [s for s in sources if s.enabled]
        if not enabled:
            task.last_result = "Error: No enabled sources found"
            self._log(task.id, f"[Pipeline] {task.last_result}")
            return

        self._log(task.id, f"[Pipeline] Fetching from {len(enabled)} sources...")

        # --- Step 2: Fetch + summarize ---
        fetcher = SourceFetcher(api_key=api_key, model_name="gemini-2.5-flash")
        cutoff_hours = task.custom_hours if task.custom_hours else 24
        cutoff = datetime.now() - timedelta(hours=cutoff_hours)
        items = fetcher.fetch_all_sources(enabled, cutoff)

        if not items:
            task.last_result = "No items found from sources"
            task.items_extracted = 0
            self._log(task.id, f"[Pipeline] {task.last_result}")
            return

        self._log(task.id, f"[Pipeline] Fetched {len(items)} items, formatting for audio...")

        # --- Step 3: Format for audio ---
        text = format_items_for_audio(items)
        if not text.strip():
            task.last_result = f"Fetched {len(items)} items but text was empty"
            task.items_extracted = len(items)
            self._log(task.id, f"[Pipeline] {task.last_result}")
            return

        # --- Step 4: Save summary text ---
        import datetime as dt_module
        today = dt_module.date.today()
        year, week, _ = today.isocalendar()
        week_folder = os.path.join(data_dir, f"Week_{week}_{year}")
        os.makedirs(week_folder, exist_ok=True)

        summary_path = os.path.join(week_folder, "summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(text)
        self._log(task.id, f"[Pipeline] Saved summary ({len(text)} chars) to {week_folder}")

        # --- Step 5: Generate audio (skip in server mode) ---
        audio_file = None
        if not self.server_mode:
            audio_filename = f"briefing_{today.isoformat()}.mp3"
            output_path = os.path.join(week_folder, audio_filename)

            self._log(task.id, f"[Pipeline] Generating audio ({task.audio_quality})...")

            if getattr(sys, "frozen", False):
                # FROZEN MODE: Run audio generation in-process via module import
                # (subprocess can't access bundled .py scripts)
                try:
                    import importlib
                    import io
                    from contextlib import redirect_stdout, redirect_stderr

                    old_argv = sys.argv
                    old_cwd = os.getcwd()
                    stdout_capture = io.StringIO()
                    stderr_capture = io.StringIO()

                    if task.audio_quality == "fast":
                        sys.argv = ["make_audio_fast.py",
                                    "--input", summary_path,
                                    "--output", output_path]
                        module_name = "make_audio_fast"
                    else:
                        sys.argv = ["make_audio_quality.py",
                                    "--input", summary_path,
                                    "--voice", task.audio_voice,
                                    "--output", output_path,
                                    "--format", "mp3"]
                        module_name = "make_audio_quality"

                    os.chdir(fm.base_dir)
                    try:
                        mod = importlib.import_module(module_name)
                        importlib.reload(mod)
                        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                            mod.main()
                    except SystemExit:
                        pass  # argparse or script called sys.exit(0)
                    finally:
                        sys.argv = old_argv
                        os.chdir(old_cwd)

                    # Check if file was created (may be .wav if MP3 conversion failed)
                    if os.path.exists(output_path):
                        audio_file = output_path
                    elif os.path.exists(output_path.replace(".mp3", ".wav")):
                        audio_file = output_path.replace(".mp3", ".wav")

                    if audio_file:
                        size_mb = os.path.getsize(audio_file) / (1024 * 1024)
                        self._log(task.id, f"[Pipeline] Audio generated: {os.path.basename(audio_file)} ({size_mb:.1f}MB)")
                    else:
                        out = stdout_capture.getvalue() + stderr_capture.getvalue()
                        self._log(task.id, f"[Pipeline] Audio generation failed (frozen): {out[:200]}")

                except Exception as audio_err:
                    self._log(task.id, f"[Pipeline] Audio error (frozen): {audio_err}")
            else:
                # DEVELOPMENT MODE: Run audio script via subprocess
                try:
                    import subprocess as sp

                    if task.audio_quality == "fast":
                        script_name = "make_audio_fast.py"
                    else:
                        script_name = "make_audio_quality.py"

                    script_path = os.path.join(script_dir, script_name)
                    cmd = [sys.executable, script_path,
                           "--input", summary_path, "--output", output_path]
                    if task.audio_quality == "quality":
                        cmd += ["--voice", task.audio_voice, "--format", "mp3"]

                    result = sp.run(
                        cmd, capture_output=True, text=True,
                        cwd=script_dir, timeout=600
                    )

                    # Check if file was created (may be .wav if MP3 conversion failed)
                    if os.path.exists(output_path):
                        audio_file = output_path
                    elif os.path.exists(output_path.replace(".mp3", ".wav")):
                        audio_file = output_path.replace(".mp3", ".wav")

                    if audio_file:
                        size_mb = os.path.getsize(audio_file) / (1024 * 1024)
                        self._log(task.id, f"[Pipeline] Audio generated: {os.path.basename(audio_file)} ({size_mb:.1f}MB)")
                    else:
                        error_msg = (result.stderr or result.stdout or "Unknown error")[:200]
                        self._log(task.id, f"[Pipeline] Audio generation failed: {error_msg}")

                except sp.TimeoutExpired:
                    self._log(task.id, "[Pipeline] Audio generation timed out (600s)")
                except Exception as audio_err:
                    self._log(task.id, f"[Pipeline] Audio error: {audio_err}")
        else:
            self._log(task.id, "[Pipeline] Server mode — skipping audio generation")

        # --- Step 6: Upload to Google Drive ---
        drive_uploaded = False
        if task.upload_to_drive and audio_file and task.drive_folder_id:
            try:
                from drive_manager import upload_file, is_signed_in, extract_folder_id_from_url
                if is_signed_in():
                    folder_id = extract_folder_id_from_url(task.drive_folder_id)
                    result = upload_file(audio_file, folder_id)
                    if result.get("status") == "uploaded":
                        drive_uploaded = True
                        self._log(task.id, f"[Pipeline] Uploaded to Drive: {result.get('name')}")
                    elif result.get("status") == "skipped":
                        drive_uploaded = True
                        self._log(task.id, f"[Pipeline] Already on Drive (skipped)")
                    else:
                        self._log(task.id, f"[Pipeline] Drive upload issue: {result}")
                else:
                    self._log(task.id, "[Pipeline] Drive not signed in — skipping upload")
            except Exception as drive_err:
                self._log(task.id, f"[Pipeline] Drive upload error: {drive_err}")
        elif task.upload_to_drive and not audio_file:
            self._log(task.id, "[Pipeline] No audio file to upload")

        # --- Step 7: Update task result ---
        task.items_extracted = len(items)
        parts = [f"{len(items)} items"]
        if audio_file:
            parts.append("audio generated")
        elif self.server_mode:
            parts.append("audio skipped (server)")
        else:
            parts.append("audio failed")
        if drive_uploaded:
            parts.append("uploaded to Drive")
        task.last_result = f"OK: {', '.join(parts)}"
        self._log(task.id, f"[Pipeline] Complete: {task.last_result}")

    def backfill_task(self, task_id: str, stop_flag: Optional[Callable] = None) -> bool:
        """
        Backfill historical data for a task by crawling the archive.

        Finds the last date_published in the target sheet, then processes all
        newsletter issues from that date forward, one at a time, with dedup.

        Args:
            task_id: ID of the task to backfill
            stop_flag: Optional callable that returns True to abort mid-backfill

        Returns:
            True if started successfully
        """
        task = self.get_task(task_id)
        if not task:
            return False

        def _run_backfill():
            if task.id in self._running_tasks:
                self._log(task.id, "[Backfill] Skipping — this task is already running")
                return
            self._running_tasks.add(task.id)

            from api_usage_tracker import set_current_task, clear_current_task
            set_current_task(task.id, task.name)

            try:
                from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions
                from sheets_manager import (
                    export_items_to_sheet, is_sheets_available, resolve_sheet_name,
                    get_last_date_in_sheet, get_covered_dates_in_sheet,
                    deduplicate_sheet, sort_sheet_by_date
                )

                # Load extraction config
                custom_instructions = None
                if task.config_name != "Default":
                    config_file = task.config_name.lower().replace(" ", "_") + ".json"
                    config_path = os.path.join(os.path.dirname(__file__), "extraction_instructions", config_file)
                    if os.path.exists(config_path):
                        custom_instructions = load_custom_instructions(config_path)

                # Determine the source URL base
                source_url = task.source_url.strip()
                if source_url and not source_url.startswith(('http://', 'https://')):
                    source_url = 'https://' + source_url

                # Find the extractor for this URL
                config = ExtractionConfig()
                processor = DataCSVProcessor(config)
                extractor = processor._get_extractor(source_url)

                if not hasattr(extractor, 'get_archive_posts'):
                    self._log(task.id, "[Backfill] This source type doesn't support archive backfill")
                    if self._on_task_complete:
                        self._on_task_complete(task, False, "Backfill not supported for this source type")
                    return

                # Check Sheets
                if not task.export_to_sheets or not task.spreadsheet_id:
                    self._log(task.id, "[Backfill] Task has no Sheets export configured")
                    return

                if not is_sheets_available():
                    self._log(task.id, "[Backfill] Google Sheets not configured")
                    return

                # Resolve sheet name
                resolved_name = resolve_sheet_name(task.spreadsheet_id, task.sheet_name)
                if not resolved_name:
                    self._log(task.id, f"[Backfill] Sheet tab '{task.sheet_name}' not found")
                    return
                if resolved_name != task.sheet_name:
                    task.sheet_name = resolved_name

                # Clean up duplicates and empty rows first
                self._log(task.id, "[Backfill] Cleaning up duplicates and empty rows...")
                dedup_result = deduplicate_sheet(task.spreadsheet_id, task.sheet_name)
                removed = dedup_result.get('removed_count', 0) if isinstance(dedup_result, dict) else 0
                if removed > 0:
                    self._log(task.id, f"[Backfill] Removed {removed} duplicate/empty rows")

                # Get dates already covered in the sheet
                covered_dates = get_covered_dates_in_sheet(task.spreadsheet_id, task.sheet_name)
                if covered_dates:
                    earliest = min(covered_dates)
                    latest = max(covered_dates)
                    self._log(task.id, f"[Backfill] Sheet has {len(covered_dates)} dates covered ({earliest} to {latest})")
                    # Fetch archive from the earliest date — to find gaps
                    since_date = earliest
                else:
                    self._log(task.id, "[Backfill] Sheet is empty — fetching entire archive")
                    since_date = None

                # Get all archive posts
                posts = extractor.get_archive_posts(
                    source_url,
                    since_date=since_date,
                    on_progress=lambda msg: self._log(task.id, msg)
                )

                if not posts:
                    self._log(task.id, "[Backfill] No posts found to backfill")
                    task.last_result = "Backfill: No new posts found"
                    self.save_tasks()
                    if self._on_task_complete:
                        self._on_task_complete(task, True, task.last_result)
                    return

                # Filter to only posts whose dates are NOT already in the sheet
                # Posts without dates are included (we can't know if they're covered)
                if covered_dates:
                    missing_posts = [
                        p for p in posts
                        if not p.get('date') or p['date'] not in covered_dates
                    ]
                    skipped = len(posts) - len(missing_posts)
                    if skipped > 0:
                        self._log(task.id, f"[Backfill] Skipping {skipped} posts (dates already in sheet)")
                    posts = missing_posts

                if not posts:
                    self._log(task.id, "[Backfill] All dates are already covered — nothing to backfill")
                    task.last_result = "Backfill: All dates covered"
                    self.save_tasks()
                    if self._on_task_complete:
                        self._on_task_complete(task, True, task.last_result)
                    return

                self._log(task.id, f"[Backfill] Processing {len(posts)} missing posts...")

                # Get columns: task override > config default
                columns = task.custom_columns
                if not columns and custom_instructions:
                    columns = custom_instructions.get('csv_columns')

                total_items = 0
                total_new_rows = 0
                errors = 0

                for i, post in enumerate(posts, 1):
                    # Check stop flag
                    if stop_flag and stop_flag():
                        self._log(task.id, f"[Backfill] Stopped by user after {i-1}/{len(posts)} posts")
                        break

                    post_url = post['url']
                    post_date = post.get('date', '?')
                    self._log(task.id, f"[Backfill] [{i}/{len(posts)}] {post_date}: {post_url[-50:]}...")

                    try:
                        # Extract items from this single post
                        items = processor.process_url(post_url, custom_instructions)
                        if not items:
                            self._log(task.id, f"[Backfill]   → 0 items (empty)")
                            continue

                        total_items += len(items)

                        # Grid enrichment
                        if task.enrich_with_grid:
                            try:
                                items = processor.enrich_with_grid(items)
                            except Exception:
                                pass

                        # Research articles
                        if task.research_articles:
                            try:
                                items = processor.research_articles(items, all_items=True)
                            except Exception:
                                pass

                        # Export to Sheets (dedup handles overlap)
                        result = export_items_to_sheet(
                            items=items,
                            spreadsheet_id=task.spreadsheet_id,
                            sheet_name=task.sheet_name,
                            columns=columns,
                            include_headers=task.include_headers
                        )

                        new_rows = result.get('updates', {}).get('updatedRows', 0)
                        if isinstance(new_rows, dict):
                            new_rows = 0
                        total_new_rows += new_rows
                        self._log(task.id, f"[Backfill]   → {len(items)} items, {new_rows} new rows")

                    except Exception as e:
                        errors += 1
                        self._log(task.id, f"[Backfill]   → Error: {str(e)[:80]}")

                    # Brief pause between posts to avoid hammering APIs
                    import time as _time
                    _time.sleep(1)

                    # Garbage collection every 5 posts
                    if i % 5 == 0:
                        gc.collect()

                task.last_result = f"Backfill: {total_items} items from {len(posts)} posts → {total_new_rows} new rows"
                if errors:
                    task.last_result += f" ({errors} errors)"
                self._log(task.id, f"[Backfill] Complete: {task.last_result}")

                # Final dedup + sort
                try:
                    dedup_result = deduplicate_sheet(task.spreadsheet_id, task.sheet_name)
                    removed = dedup_result.get('removed_count', 0) if isinstance(dedup_result, dict) else 0
                    if removed > 0:
                        self._log(task.id, f"[Backfill] Final cleanup: {removed} duplicate/empty rows removed")
                    sort_sheet_by_date(task.spreadsheet_id, task.sheet_name)
                    self._log(task.id, "[Backfill] Sheet sorted by date")
                except Exception as cleanup_err:
                    self._log(task.id, f"[Backfill] Cleanup warning: {cleanup_err}")

                task.last_run = datetime.now().isoformat()
                self.save_tasks()

                if self._on_task_complete:
                    self._on_task_complete(task, True, task.last_result)

            except Exception as e:
                self._log(task.id, f"[Backfill] Fatal error: {e}")
                task.last_result = f"Backfill error: {str(e)[:100]}"
                self.save_tasks()
                if self._on_task_complete:
                    self._on_task_complete(task, False, task.last_result)
            finally:
                clear_current_task()
                self._running_tasks.discard(task.id)
                gc.collect()

        threading.Thread(target=_run_backfill, daemon=True).start()
        return True

    def reenrich_task(self, task_id: str, stop_flag: Optional[Callable] = None) -> bool:
        """Re-enrich existing sheet rows that are missing Grid data.

        Reads rows from the sheet, identifies those without grid_matched,
        runs Grid enrichment on them, and writes grid columns back.

        Args:
            task_id: The task to re-enrich
            stop_flag: Optional callable that returns True to stop

        Returns:
            True if re-enrichment started successfully.
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task.id in self._running_tasks:
            self._log(task.id, "[Re-enrich] This task is already running")
            return False

        if not task.spreadsheet_id:
            self._log(task.id, "[Re-enrich] No spreadsheet configured")
            return False

        self._running_tasks.add(task.id)

        def _run_reenrich():
            from api_usage_tracker import set_current_task, clear_current_task
            set_current_task(task.id, task.name)

            try:
                from sheets_manager import (
                    get_sheets_service, get_sheet_headers,
                    sort_sheet_by_date
                )
                from data_csv_processor import DataCSVProcessor, ExtractionConfig, ExtractedItem

                self._log(task.id, "[Re-enrich] Reading sheet data...")

                service = get_sheets_service()
                result = service.spreadsheets().values().get(
                    spreadsheetId=task.spreadsheet_id,
                    range=f"'{task.sheet_name}'!A:Z"
                ).execute()

                rows = result.get('values', [])
                if len(rows) < 2:
                    self._log(task.id, "[Re-enrich] No data rows found")
                    return

                headers = rows[0]
                data_rows = rows[1:]

                # Find column indices
                url_idx = headers.index('url') if 'url' in headers else -1
                desc_idx = headers.index('description') if 'description' in headers else -1
                source_idx = headers.index('source_name') if 'source_name' in headers else -1
                date_idx = headers.index('date_published') if 'date_published' in headers else -1
                skip_idx = headers.index('SKIP') if 'SKIP' in headers else -1
                grid_matched_idx = headers.index('grid_matched') if 'grid_matched' in headers else -1

                if url_idx < 0 or desc_idx < 0:
                    self._log(task.id, "[Re-enrich] Missing url or description column")
                    return

                # Find grid column indices for writing back
                grid_cols = [h for h in headers if h.startswith('grid_')]
                grid_col_indices = {h: headers.index(h) for h in grid_cols}
                comments_idx = headers.index('comments') if 'comments' in headers else -1

                self._log(task.id, f"[Re-enrich] Sheet has {len(data_rows)} rows, {len(grid_cols)} grid columns")

                # Identify rows needing enrichment (grid_matched is empty or missing)
                unenriched = []
                for row_num, row in enumerate(data_rows, start=2):  # row 2 = first data row
                    # Skip if SKIP=TRUE
                    if skip_idx >= 0 and len(row) > skip_idx:
                        if str(row[skip_idx]).strip().upper() == 'TRUE':
                            continue

                    # Check if grid_matched is empty
                    has_grid = False
                    if grid_matched_idx >= 0 and len(row) > grid_matched_idx:
                        val = str(row[grid_matched_idx]).strip().upper()
                        if val in ('TRUE', 'FALSE'):
                            has_grid = True

                    if not has_grid:
                        url_val = row[url_idx] if len(row) > url_idx else ''
                        desc_val = row[desc_idx] if len(row) > desc_idx else ''
                        source_val = row[source_idx] if source_idx >= 0 and len(row) > source_idx else ''
                        date_val = row[date_idx] if date_idx >= 0 and len(row) > date_idx else ''

                        if url_val.strip():
                            unenriched.append({
                                'row_num': row_num,
                                'url': url_val.strip(),
                                'description': desc_val,
                                'source_name': source_val,
                                'date_published': date_val,
                            })

                self._log(task.id, f"[Re-enrich] Found {len(unenriched)} unenriched rows")

                if not unenriched:
                    self._log(task.id, "[Re-enrich] All rows already enriched — nothing to do")
                    return

                # Process in batches of 50
                config = ExtractionConfig()
                processor = DataCSVProcessor(config)
                batch_size = 50
                total_matched = 0
                total_processed = 0

                for batch_start in range(0, len(unenriched), batch_size):
                    if stop_flag and stop_flag():
                        self._log(task.id, "[Re-enrich] Stopped by user")
                        break

                    batch = unenriched[batch_start:batch_start + batch_size]

                    # Create ExtractedItem objects
                    items = []
                    for entry in batch:
                        item = ExtractedItem(
                            url=entry['url'],
                            description=entry['description'],
                            source_name=entry['source_name'],
                            date_published=entry['date_published'],
                            title=entry['description'][:80] if entry['description'] else '',
                        )
                        items.append(item)

                    # Enrich with Grid
                    try:
                        items = processor.enrich_with_grid(items)
                    except Exception as e:
                        self._log(task.id, f"[Re-enrich] Grid error on batch {batch_start}: {e}")
                        continue

                    # Helper: convert 0-based column index to A1 notation letter(s)
                    def _col_letter(idx):
                        """Convert 0-based column index to spreadsheet column letter (A, B, ..., Z, AA, AB, ...)."""
                        result = ''
                        while True:
                            result = chr(65 + idx % 26) + result
                            idx = idx // 26 - 1
                            if idx < 0:
                                break
                        return result

                    # Write grid columns back to sheet
                    updates = []
                    for item, entry in zip(items, batch):
                        row_num = entry['row_num']
                        item_dict = item.to_dict()

                        for col_name, col_idx in grid_col_indices.items():
                            col_letter = _col_letter(col_idx)
                            val = str(item_dict.get(col_name, ''))
                            updates.append({
                                'range': f"'{task.sheet_name}'!{col_letter}{row_num}",
                                'values': [[val]]
                            })

                        # Also write comments if available
                        if comments_idx >= 0:
                            comments_val = item_dict.get('comments', '')
                            if comments_val:
                                col_letter = _col_letter(comments_idx)
                                updates.append({
                                    'range': f"'{task.sheet_name}'!{col_letter}{row_num}",
                                    'values': [[comments_val]]
                                })

                        if item.custom_fields.get('grid_matched'):
                            total_matched += 1

                    # Batch write to sheet
                    if updates:
                        # Write in sub-batches of 500 cells
                        for i in range(0, len(updates), 500):
                            chunk = updates[i:i + 500]
                            service.spreadsheets().values().batchUpdate(
                                spreadsheetId=task.spreadsheet_id,
                                body={
                                    'valueInputOption': 'RAW',
                                    'data': chunk
                                }
                            ).execute()

                    total_processed += len(batch)
                    self._log(task.id, f"[Re-enrich] Processed {total_processed}/{len(unenriched)} rows ({total_matched} matched so far)")

                    gc.collect()
                    import time as _time
                    _time.sleep(0.5)

                task.last_result = f"Re-enrich: {total_processed} rows processed, {total_matched} matched"
                self._log(task.id, f"[Re-enrich] Complete: {task.last_result}")
                self.save_tasks()

                if self._on_task_complete:
                    self._on_task_complete(task, True, task.last_result)

            except Exception as e:
                self._log(task.id, f"[Re-enrich] Fatal error: {e}")
                task.last_result = f"Re-enrich error: {str(e)[:100]}"
                self.save_tasks()
                if self._on_task_complete:
                    self._on_task_complete(task, False, task.last_result)
            finally:
                clear_current_task()
                self._running_tasks.discard(task.id)
                gc.collect()

        threading.Thread(target=_run_reenrich, daemon=True).start()
        return True

    def retitle_task(self, task_id: str, stop_flag: Optional[Callable] = None) -> bool:
        """Re-fetch source posts and update truncated titles in the sheet.

        For Telegram tasks, paginates through all historical messages to build
        a URL→full_title map, then updates truncated sheet titles.

        Args:
            task_id: The task to re-title
            stop_flag: Optional callable that returns True to stop

        Returns:
            True if retitle started successfully.
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task.id in self._running_tasks:
            self._log(task.id, "[Re-title] This task is already running")
            return False

        if not task.spreadsheet_id:
            self._log(task.id, "[Re-title] No spreadsheet configured")
            return False

        self._running_tasks.add(task.id)

        def _run_retitle():
            from api_usage_tracker import set_current_task, clear_current_task
            set_current_task(task.id, task.name)

            try:
                from data_csv_processor import DataCSVProcessor, ExtractionConfig
                from sheets_manager import get_sheets_service, get_sheet_headers

                self._log(task.id, "[Re-title] Fetching source posts page by page...")

                # Manual pagination so we can check stop_flag between pages
                import requests as _requests
                from bs4 import BeautifulSoup

                config = ExtractionConfig()
                processor = DataCSVProcessor(config)

                # Get the Telegram extractor
                extractor = None
                for ext in processor.extractors:
                    if ext.name == 'telegram':
                        extractor = ext
                        break

                if not extractor:
                    self._log(task.id, "[Re-title] No Telegram extractor found")
                    return

                # Preprocess URL to t.me/s/ format
                source_url = extractor.preprocess_url(task.source_url)

                items = []
                seen_urls = set()
                oldest_id = None
                max_pages = 50  # Safety cap

                for page_num in range(max_pages):
                    if stop_flag and stop_flag():
                        self._log(task.id, f"[Re-title] Stopped after {page_num} pages ({len(items)} posts)")
                        break

                    fetch_url = source_url
                    if oldest_id:
                        fetch_url = f"{source_url}?before={oldest_id}"

                    try:
                        resp = _requests.get(fetch_url, timeout=15, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        })
                        html = resp.text
                    except Exception as e:
                        self._log(task.id, f"[Re-title] Fetch error on page {page_num}: {e}")
                        break

                    if not html:
                        break

                    page_items = extractor.extract(fetch_url, html)
                    if not page_items:
                        break

                    new_count = 0
                    for item in page_items:
                        if item.url not in seen_urls:
                            seen_urls.add(item.url)
                            items.append(item)
                            new_count += 1

                    # Find oldest message ID for next page
                    soup = BeautifulSoup(html, 'html.parser')
                    msg_ids = []
                    for msg in soup.find_all('div', class_='tgme_widget_message_wrap'):
                        msg_link = msg.find('a', class_='tgme_widget_message_date')
                        if msg_link:
                            href = msg_link.get('href', '')
                            if '/' in href:
                                try:
                                    msg_ids.append(int(href.split('/')[-1]))
                                except ValueError:
                                    pass

                    if not msg_ids:
                        break

                    new_oldest = min(msg_ids)
                    if oldest_id and new_oldest >= oldest_id:
                        break
                    oldest_id = new_oldest

                    self._log(task.id, f"[Re-title] Page {page_num + 1}: {new_count} new posts (total: {len(items)})")

                    import time as _time
                    _time.sleep(0.5)

                self._log(task.id, f"[Re-title] Fetched {len(items)} posts total")

                if stop_flag and stop_flag():
                    self._log(task.id, "[Re-title] Stopped by user")
                    task.last_result = f"Re-title: stopped after fetching {len(items)} posts"
                    self.save_tasks()
                    return

                if not items:
                    self._log(task.id, "[Re-title] No posts fetched — nothing to update")
                    return

                # Build URL → full title map
                url_to_title = {}
                for item in items:
                    if item.url and item.title:
                        url_to_title[item.url.strip()] = item.title
                self._log(task.id, f"[Re-title] Built map of {len(url_to_title)} URL→title pairs")

                # Read sheet data
                service = get_sheets_service()
                headers = get_sheet_headers(task.spreadsheet_id, task.sheet_name)
                if not headers:
                    self._log(task.id, "[Re-title] No headers found in sheet")
                    return

                title_idx = headers.index('title') if 'title' in headers else -1
                url_idx = headers.index('url') if 'url' in headers else -1

                if title_idx < 0 or url_idx < 0:
                    self._log(task.id, "[Re-title] Missing 'title' or 'url' column")
                    return

                # Read all data
                result = service.spreadsheets().values().get(
                    spreadsheetId=task.spreadsheet_id,
                    range=f"'{task.sheet_name}'!A:Z"
                ).execute()

                rows = result.get('values', [])
                if len(rows) < 2:
                    self._log(task.id, "[Re-title] No data rows")
                    return

                data_rows = rows[1:]
                title_col_letter = chr(65 + title_idx) if title_idx < 26 else chr(64 + title_idx // 26) + chr(65 + title_idx % 26)

                # Find truncated titles and match to full titles
                updates = []
                for row_num, row in enumerate(data_rows, start=2):
                    if stop_flag and stop_flag():
                        self._log(task.id, "[Re-title] Stopped by user")
                        break

                    if len(row) <= max(title_idx, url_idx):
                        continue

                    current_title = row[title_idx] if len(row) > title_idx else ''
                    row_url = row[url_idx].strip() if len(row) > url_idx else ''

                    # Only update if title appears truncated
                    if not current_title or '...' not in current_title:
                        continue

                    # Look up full title
                    full_title = url_to_title.get(row_url, '')
                    if full_title and full_title != current_title:
                        updates.append({
                            'range': f"'{task.sheet_name}'!{title_col_letter}{row_num}",
                            'values': [[full_title]]
                        })

                self._log(task.id, f"[Re-title] Found {len(updates)} titles to update")

                if not updates:
                    self._log(task.id, "[Re-title] No truncated titles matched — nothing to update")
                    task.last_result = f"Re-title: 0 titles updated (no matches in {len(url_to_title)} fetched posts)"
                    self.save_tasks()
                    if self._on_task_complete:
                        self._on_task_complete(task, True, task.last_result)
                    return

                # Batch write updates (500 cells per batch)
                total_written = 0
                for i in range(0, len(updates), 500):
                    chunk = updates[i:i + 500]
                    service.spreadsheets().values().batchUpdate(
                        spreadsheetId=task.spreadsheet_id,
                        body={
                            'valueInputOption': 'RAW',
                            'data': chunk
                        }
                    ).execute()
                    total_written += len(chunk)
                    self._log(task.id, f"[Re-title] Updated {total_written}/{len(updates)} titles")

                task.last_result = f"Re-title: {len(updates)} titles updated from {len(url_to_title)} fetched posts"
                self._log(task.id, f"[Re-title] Complete: {task.last_result}")
                self.save_tasks()

                if self._on_task_complete:
                    self._on_task_complete(task, True, task.last_result)

            except Exception as e:
                self._log(task.id, f"[Re-title] Fatal error: {e}")
                import traceback
                traceback.print_exc()
                task.last_result = f"Re-title error: {str(e)[:100]}"
                self.save_tasks()
                if self._on_task_complete:
                    self._on_task_complete(task, False, task.last_result)
            finally:
                clear_current_task()
                self._running_tasks.discard(task.id)
                gc.collect()

        threading.Thread(target=_run_retitle, daemon=True).start()
        return True

    def run_task_now(self, task_id: str) -> bool:
        """Manually trigger a task to run immediately."""
        task = self.get_task(task_id)
        if task:
            # Run in background thread to not block UI
            threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()
            return True
        return False


# Global scheduler instance
_scheduler: Optional[Scheduler] = None


def get_scheduler(on_task_complete: Optional[Callable] = None,
                  on_progress: Optional[Callable] = None,
                  server_mode: bool = False, data_dir: Optional[str] = None) -> Scheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(on_task_complete, on_progress=on_progress,
                               server_mode=server_mode, data_dir=data_dir)
    else:
        if on_task_complete:
            _scheduler._on_task_complete = on_task_complete
        if on_progress:
            _scheduler._on_progress = on_progress
    return _scheduler
