"""
Scheduler Module - Background extraction and export automation

This module provides:
1. Scheduled task management (create, edit, delete, enable/disable)
2. Background thread that runs tasks at configured intervals
3. Auto-extraction from configured sources
4. Auto-export to Google Sheets
"""

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
                 server_mode: bool = False, data_dir: Optional[str] = None):
        """
        Initialize the scheduler.

        Args:
            on_task_complete: Callback function(task, success, message) called after each task runs
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
        self._lock = threading.Lock()

        self.load_tasks()

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
        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                with self._lock:
                    for task in self.tasks:
                        if not task.enabled or not task.next_run:
                            continue

                        try:
                            next_run = datetime.fromisoformat(task.next_run)
                            if now >= next_run:
                                # Time to run this task
                                self._execute_task(task)
                        except Exception as e:
                            print(f"[Scheduler] Error checking task {task.name}: {e}")

                # Check every 30 seconds
                self._stop_event.wait(30)

            except Exception as e:
                print(f"[Scheduler] Error in run loop: {e}")
                self._stop_event.wait(60)

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        print(f"[Scheduler] Running task: {task.name}")
        task.last_run = datetime.now().isoformat()

        try:
            # Import here to avoid circular imports
            from data_csv_processor import DataCSVProcessor, ExtractionConfig, load_custom_instructions

            # Create processor
            config = ExtractionConfig()
            processor = DataCSVProcessor(config)

            # Load custom instructions if not default
            custom_instructions = None
            if task.config_name != "Default":
                config_file = task.config_name.lower().replace(" ", "_") + ".json"
                config_path = os.path.join(os.path.dirname(__file__), "extraction_instructions", config_file)
                if os.path.exists(config_path):
                    custom_instructions = load_custom_instructions(config_path)

            # Normalize URL - ensure it has a scheme
            source_url = task.source_url.strip()
            if source_url and not source_url.startswith(('http://', 'https://')):
                source_url = 'https://' + source_url

            # Extract items
            items = processor.process_url(source_url, custom_instructions)
            task.items_extracted = len(items)

            # Export to Google Sheets if enabled
            if task.export_to_sheets and items and task.spreadsheet_id:
                try:
                    from sheets_manager import (
                        export_items_to_sheet, is_sheets_available, resolve_sheet_name
                    )

                    if is_sheets_available():
                        # Auto-detect renamed sheet tabs
                        resolved_name = resolve_sheet_name(task.spreadsheet_id, task.sheet_name)
                        if resolved_name and resolved_name != task.sheet_name:
                            print(f"[Scheduler] Sheet tab renamed: '{task.sheet_name}' → '{resolved_name}'")
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
                    else:
                        task.last_result = f"Extracted {len(items)} items (Sheets not configured)"
                except Exception as e:
                    task.last_result = f"Extracted {len(items)} items, Sheets error: {str(e)[:50]}"
            else:
                task.last_result = f"Success: Extracted {len(items)} items"

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

            print(f"[Scheduler] Task failed: {e}")

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
                  server_mode: bool = False, data_dir: Optional[str] = None) -> Scheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(on_task_complete, server_mode=server_mode, data_dir=data_dir)
    elif on_task_complete:
        _scheduler._on_task_complete = on_task_complete
    return _scheduler
