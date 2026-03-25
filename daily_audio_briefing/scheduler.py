# Source Generated with Decompyle++
# File: scheduler.pyc (Python 3.12)

'''
Scheduler Module - Background extraction and export automation

This module provides:
1. Scheduled task management (create, edit, delete, enable/disable)
2. Background thread that runs tasks at configured intervals
3. Auto-extraction from configured sources
4. Auto-export to Google Sheets
'''
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
    '''Supported scheduling intervals.'''
    HOURLY = 'hourly'
    EVERY_6_HOURS = 'every_6_hours'
    EVERY_12_HOURS = 'every_12_hours'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    CUSTOM_HOURS = 'custom_hours'

ScheduledTask = <NODE:12>()

def get_scheduler_config_path(data_dir = None):
    '''Get path to scheduler configuration file.

    Args:
        data_dir: Override data directory (used in server mode).
                  If None, uses frozen app or development mode paths.
    '''
    if data_dir:
        os.makedirs(data_dir, exist_ok = True)
        return os.path.join(data_dir, 'scheduled_tasks.json')
    if None(sys, 'frozen', False):
        if sys.platform == 'darwin':
            app_support = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            app_support = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            app_support = os.path.expanduser('~/.daily-audio-briefing')
        os.makedirs(app_support, exist_ok = True)
        return os.path.join(app_support, 'scheduled_tasks.json')
    return None.path.join(os.path.dirname(__file__), 'scheduled_tasks.json')


class Scheduler:
    '''Background scheduler for automated extraction tasks.'''
    
    def __init__(self, on_task_complete = None, on_progress = None, on_task_start = None, server_mode = (None, None, None, False, None), data_dir = ('on_task_complete', Optional[Callable], 'on_progress', Optional[Callable], 'on_task_start', Optional[Callable], 'server_mode', bool, 'data_dir', Optional[str])):
        '''
        Initialize the scheduler.

        Args:
            on_task_complete: Callback function(task, success, message) called after each task runs
            on_progress: Callback function(task_id, message) called with progress log lines during execution
            on_task_start: Callback function(task) called when a task begins executing
            server_mode: If True, log to stdout and skip OS-level daemon operations
            data_dir: Override data directory for config/task files (used in server mode)
        '''
        self.tasks = []
        self.running = False
        self.server_mode = server_mode
        self.data_dir = data_dir
        self._thread = None
        self._stop_event = threading.Event()
        self._on_task_complete = on_task_complete
        self._on_task_start = on_task_start
        self._on_progress = on_progress
        self._lock = threading.Lock()
        self._running_tasks = set()
        self._tasks_loaded = False
        if not server_mode:
            self.load_tasks()
            self._tasks_loaded = True
            return None

    
    def load_tasks(self):
        '''Load scheduled tasks with multi-tier fallback.

        Priority:
        1. Config file on disk (always preferred if it exists)
        2. Google Sheets _scheduler_config tab (survives Render redeploys)
        3. SCHEDULED_TASKS_JSON env var (initial seed / emergency fallback)
        '''
        config_path = get_scheduler_config_path(self.data_dir)
        loaded_from = None
    # WARNING: Decompyle incomplete

    
    def _write_tasks_to_file(self = None, config_path = None):
        '''Write tasks to file (internal helper).'''
        pass
    # WARNING: Decompyle incomplete

    
    def save_tasks(self):
        '''Save scheduled tasks to config file and (in server mode) to Google Sheets.'''
        config_path = get_scheduler_config_path(self.data_dir)
    # WARNING: Decompyle incomplete

    
    def _save_task_field(self = None, task_id = None, field_name = None, value = ('task_id', str, 'field_name', str)):
        '''Persist a single field for a task directly to the config file.

        Bypasses self.tasks serialization to avoid stale-reference races
        when load_tasks() replaces self.tasks during long-running executions.
        '''
        config_path = get_scheduler_config_path(self.data_dir)
    # WARNING: Decompyle incomplete

    
    def _apply_task_state(self = None, task = None):
        """Copy runtime state from a (possibly stale) task reference to the
        current matching task in self.tasks.

        When load_tasks() replaces self.tasks during a long-running execution,
        the 'task' parameter may be an old object no longer in self.tasks.
        This syncs its updated fields onto the current list before save_tasks().
        """
        for t in self.tasks:
            if not t.id == task.id:
                continue
            t.last_run = task.last_run
            t.last_result = task.last_result
            t.next_run = task.next_run
            t.items_extracted = task.items_extracted
            t.daily_run_count = task.daily_run_count
            t.daily_run_date = task.daily_run_date
            self.tasks
            return None

    
    def _get_persistence_sheet_id(self = None):
        '''Get the spreadsheet ID used for config persistence.'''
        return os.environ.get('SCHEDULER_SHEET_ID')

    
    def _save_to_sheets(self = None, data = None):
        '''Write tasks JSON to the _scheduler_config tab of the persistence sheet.'''
        sheet_id = self._get_persistence_sheet_id()
        if not sheet_id:
            return None
        is_sheets_available = is_sheets_available
        get_sheets_service = get_sheets_service
        import sheets_manager
        if not is_sheets_available():
            return None
        service = get_sheets_service()
        json_str = json.dumps(data, indent = 2)
        service.spreadsheets().values().get(spreadsheetId = sheet_id, range = '_scheduler_config!A1').execute()
        service.spreadsheets().values().update(spreadsheetId = sheet_id, range = '_scheduler_config!A1', valueInputOption = 'RAW', body = {
            'values': [
                [
                    json_str]] }).execute()
        print(f'''[Scheduler] Saved {len(data.get('tasks', []))} task(s) to Sheets persistence''')
        return None
    # WARNING: Decompyle incomplete

    
    def _load_from_sheets(self = None):
        '''Read tasks JSON from the _scheduler_config tab of the persistence sheet.'''
        sheet_id = self._get_persistence_sheet_id()
        if not sheet_id:
            return None
        is_sheets_available = is_sheets_available
        get_sheets_service = get_sheets_service
        import sheets_manager
        if not is_sheets_available():
            return None
        service = get_sheets_service()
        result = service.spreadsheets().values().get(spreadsheetId = sheet_id, range = '_scheduler_config!A1').execute()
        values = result.get('values', [])
        if values and values[0]:
            data = json.loads(values[0][0])
            print('[Scheduler] Read config from Sheets persistence')
            return data
    # WARNING: Decompyle incomplete

    
    def add_task(self = None, task = None):
        '''Add a new scheduled task.'''
        pass
    # WARNING: Decompyle incomplete

    
    def update_task(self = None, task_id = None, updates = None):
        '''Update an existing task.'''
        pass
    # WARNING: Decompyle incomplete

    
    def delete_task(self = None, task_id = None):
        '''Delete a scheduled task.'''
        pass
    # WARNING: Decompyle incomplete

    
    def get_task(self = None, task_id = None):
        '''Get a task by ID.'''
        for task in self.tasks:
            if not task.id == task_id:
                continue
            
            return self.tasks, task

    
    def _calculate_next_run(self = None, task = None):
        '''Calculate the next run time for a task.'''
        now = datetime.now()
        if task.interval == 'hourly':
            next_run = now.replace(minute = 0, second = 0, microsecond = 0) + timedelta(hours = 1)
            return next_run.isoformat()
        if None.interval == 'every_6_hours':
            current_hour = now.hour
            next_hour = (current_hour // 6 + 1) * 6
            if next_hour >= 24:
                next_run = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0) + timedelta(days = 1)
                return next_run.isoformat()
            next_run = None.replace(hour = next_hour, minute = 0, second = 0, microsecond = 0)
            return next_run.isoformat()
        if None.interval == 'every_12_hours':
            current_hour = now.hour
            if current_hour < 12:
                next_run = now.replace(hour = 12, minute = 0, second = 0, microsecond = 0)
                return next_run.isoformat()
            next_run = None.replace(hour = 0, minute = 0, second = 0, microsecond = 0) + timedelta(days = 1)
            return next_run.isoformat()
        if None.interval == 'daily':
            (hour, minute) = map(int, task.run_at_time.split(':'))
            next_run = now.replace(hour = hour, minute = minute, second = 0, microsecond = 0)
            if next_run <= now:
                next_run += timedelta(days = 1)
            return next_run.isoformat()
        if None.interval == 'weekly':
            (hour, minute) = map(int, task.run_at_time.split(':'))
            days_ahead = task.run_on_day - now.weekday()
            if (days_ahead < 0 or days_ahead == 0) and now.hour * 60 + now.minute >= hour * 60 + minute:
                days_ahead += 7
            next_run = now.replace(hour = hour, minute = minute, second = 0, microsecond = 0) + timedelta(days = days_ahead)
            return next_run.isoformat()
        if None.interval == 'custom_hours':
            next_run = now + timedelta(hours = task.custom_hours)
            return next_run.isoformat()
        next_run = None + timedelta(days = 1)
        return next_run.isoformat()
    # WARNING: Decompyle incomplete

    
    def start(self):
        '''Start the background scheduler thread.'''
        if self.running:
            return None
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target = self._run_loop, daemon = True)
        self._thread.start()
        print('[Scheduler] Started')

    
    def stop(self):
        '''Stop the background scheduler thread.'''
        if not self.running:
            return None
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout = 5)
        print('[Scheduler] Stopped')

    
    def _run_loop(self):
        '''Main scheduler loop - checks for tasks to run.'''
        if not self._tasks_loaded:
            self.load_tasks()
            self._tasks_loaded = True
        get_tracker = get_tracker
        import api_usage_tracker
        tracker = get_tracker()
        stats = tracker.get_stats()
        budget = stats.get('monthly_budget_usd', 0)
        cost = stats.get('monthly_cost_estimate', 0)
        daily = stats.get('daily_calls', 0)
        daily_limit = stats.get('daily_limit', 500)
        enabled = stats.get('limits_enabled', True)
        cooldown = stats.get('cooldown_enabled', True)
        print(f'''[Scheduler] API budget status: daily={daily}/{daily_limit}, monthly_cost=${cost:.4f}/{f'''${budget:.2f}''' if budget > 0 else 'unlimited'}, limits={'ON' if enabled else 'OFF'}, cooldown={'ON' if cooldown else 'OFF'}''')
        if budget <= 0:
            print('[Scheduler] WARNING: No monthly budget cap set! Set API_MONTHLY_BUDGET env var to prevent runaway costs.')
    # WARNING: Decompyle incomplete

    
    def _log(self = None, task_id = None, message = None):
        '''Print and optionally forward progress to the GUI callback.'''
        print(message)
        if self._on_progress:
            self._on_progress(task_id, message)
            return None
        return None
    # WARNING: Decompyle incomplete

    
    def _execute_task(self = None, task = None):
        '''Execute a scheduled task. Guarded by mutex to prevent concurrent runs.'''
        if task.id in self._running_tasks:
            print(f'''[Scheduler] Skipping \'{task.name}\' — already running''')
            return None
        self._running_tasks.add(task.id)
        MAX_DAILY_RUNS_BY_INTERVAL = {
            'hourly': 48,
            'daily': 3,
            'weekly': 3 }
        max_daily_runs = MAX_DAILY_RUNS_BY_INTERVAL.get(task.interval, 3)
        today_str = datetime.now().strftime('%Y-%m-%d')
        if task.daily_run_date == today_str:
            if task.daily_run_count >= max_daily_runs:
                msg = f'''Skipped — daily run cap reached ({task.daily_run_count}/{max_daily_runs})'''
                self._log(task.id, f'''[Scheduler] Task \'{task.name}\': {msg}''')
                task.last_result = msg
                task.next_run = self._calculate_next_run(task)
                self._apply_task_state(task)
                self.save_tasks()
                self._running_tasks.discard(task.id)
                if self._on_task_complete:
                    self._on_task_complete(task, False, msg)
                return None
        else:
            today_str = task, task.daily_run_count += 1, .daily_run_count
            task.daily_run_count = 1
        if self._on_task_start:
            self._on_task_start(task)
        set_current_task = set_current_task
        clear_current_task = clear_current_task
        get_tracker = get_tracker
        import api_usage_tracker
        tracker = get_tracker()
        if tracker.is_cooldown_active():
            stats = tracker.get_stats()
            cost = stats.get('monthly_cost_estimate', 0)
            budget = stats.get('monthly_budget_usd', 0)
            msg = f'''Skipped — API budget exhausted (${cost:.4f} / ${budget:.2f})'''
            self._log(task.id, f'''[Scheduler] Task \'{task.name}\': {msg}''')
            task.last_result = msg
            task.next_run = self._calculate_next_run(task)
            self._apply_task_state(task)
            self.save_tasks()
            self._running_tasks.discard(task.id)
            if self._on_task_complete:
                self._on_task_complete(task, False, msg)
            return None
        if not tracker.check_limit():
            stats = tracker.get_stats()
            daily = stats.get('daily_calls', 0)
            monthly = stats.get('monthly_calls', 0)
            msg = f'''Skipped — API call limit reached (daily={daily}, monthly={monthly})'''
            self._log(task.id, f'''[Scheduler] Task \'{task.name}\': {msg}''')
            task.last_result = msg
            task.next_run = self._calculate_next_run(task)
            self._apply_task_state(task)
            self.save_tasks()
            self._running_tasks.discard(task.id)
            if self._on_task_complete:
                self._on_task_complete(task, False, msg)
            return None
        set_current_task(task.id, task.name)
        self._log(task.id, f'''[Scheduler] Running task: {task.name}''')
        task.last_run = datetime.now().isoformat()
        self._save_task_field(task.id, 'last_run', task.last_run)
        self._save_task_field(task.id, 'daily_run_count', task.daily_run_count)
        self._save_task_field(task.id, 'daily_run_date', task.daily_run_date)
        if task.task_type == 'briefing_pipeline':
            pre_run_next = task.next_run
            self._execute_pipeline_task(task)
            if not task.next_run == pre_run_next or task.next_run:
                task.next_run = self._calculate_next_run(task)
            self._apply_task_state(task)
            self.save_tasks()
            if self._on_task_complete:
                is_success = not task.last_result.startswith('Error')
                self._on_task_complete(task, is_success, task.last_result)
            clear_current_task()
            self._running_tasks.discard(task.id)
            gc.collect()
            return None
        DataCSVProcessor = DataCSVProcessor
        ExtractionConfig = ExtractionConfig
        load_custom_instructions = load_custom_instructions
        import data_csv_processor
        config = ExtractionConfig()
        if self.server_mode:
            config.max_workers = 2
            config.resolve_redirects = False
        processor = DataCSVProcessor(config)
        custom_instructions = None
        if task.config_name != 'Default':
            config_file = task.config_name.lower().replace(' ', '_') + '.json'
            config_path = os.path.join(os.path.dirname(__file__), 'extraction_instructions', config_file)
            if os.path.exists(config_path):
                custom_instructions = load_custom_instructions(config_path)
                self._log(task.id, f'''[Scheduler] Loaded config: {task.config_name}''')
        source_url = task.source_url.strip()
        if not source_url and source_url.startswith(('http://', 'https://')):
            source_url = 'https://' + source_url
        self._log(task.id, f'''[Scheduler] Fetching: {source_url[:80]}...''')
        items = processor.process_url(source_url, custom_instructions)
        task.items_extracted = len(items)
        self._log(task.id, f'''[Scheduler] Extracted {len(items)} items''')
        if task.enrich_with_grid and items:
            self._log(task.id, f'''[Scheduler] Enriching {len(items)} items with Grid data...''')
            items = processor.enrich_with_grid(items)
            matched = (lambda .0: pass# WARNING: Decompyle incomplete
)(items())
            self._log(task.id, f'''[Scheduler] Grid enrichment: {matched}/{len(items)} items matched''')
        if task.research_articles and items:
            self._log(task.id, f'''[Scheduler] Researching articles for {len(items)} items...''')
            items = processor.research_articles(items, all_items = True)
            self._log(task.id, '[Scheduler] Article research complete')
        task.next_run = self._calculate_next_run(task)
        self._apply_task_state(task)
        self.save_tasks()
        if self._on_task_complete:
            self._on_task_complete(task, True, task.last_result)
        clear_current_task()
        self._running_tasks.discard(task.id)
        gc.collect()
        return None
    # WARNING: Decompyle incomplete

    
    def _execute_pipeline_task(self = None, task = None):
        '''Execute a briefing pipeline task: fetch → summarize → audio → Drive.

        Steps:
            1. Load and filter sources from sources.json
            2. Fetch + AI-summarize via SourceFetcher
            3. Format text for audio narration
            4. Save summary text to Week_N_YYYY folder
            5. Generate audio via TTS subprocess (skip in server mode)
            6. Upload audio to Google Drive (if configured)
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _pipeline_drive_upload(self, task, summary_path, audio_file, data_dir, item_count, cooldown = (0, False)):
        '''Upload pipeline output to Google Drive and update task result.

        Shared by both the normal pipeline flow and the checkpoint-resume path.
        '''
        drive_uploaded = False
        drive_error_msg = ''
        if task.upload_to_drive and task.drive_folder_id:
            upload_file = upload_file
            is_signed_in = is_signed_in
            extract_folder_id_from_url = extract_folder_id_from_url
            is_reauth_needed = is_reauth_needed
            flag_reauth_needed = flag_reauth_needed
            import drive_manager
            if is_reauth_needed():
                drive_error_msg = 'Drive token expired — re-authenticate in Settings'
                self._log(task.id, f'''[Pipeline] {drive_error_msg}''')
            elif is_signed_in():
                folder_id = extract_folder_id_from_url(task.drive_folder_id)
                uploaded_files = []
                txt_result = upload_file(summary_path, folder_id)
                if txt_result.get('status') in ('uploaded', 'skipped'):
                    uploaded_files.append(f'''summary ({txt_result['status']})''')
                else:
                    drive_error_msg = f'''txt: {txt_result.get('reason', 'unknown')}'''
                    self._log(task.id, f'''[Pipeline] Summary upload failed: {drive_error_msg}''')
                if audio_file:
                    audio_result = upload_file(audio_file, folder_id)
                    if audio_result.get('status') in ('uploaded', 'skipped'):
                        uploaded_files.append(f'''audio ({audio_result['status']})''')
                    else:
                        drive_error_msg = f'''audio: {audio_result.get('reason', 'unknown')}'''
                        self._log(task.id, f'''[Pipeline] Audio upload failed: {drive_error_msg}''')
                elif not self.server_mode:
                    self._log(task.id, '[Pipeline] No audio file to upload')
                if uploaded_files:
                    drive_uploaded = True
                    self._log(task.id, f'''[Pipeline] Uploaded to Drive: {', '.join(uploaded_files)}''')
                else:
                    drive_error_msg = 'Drive not signed in'
                    self._log(task.id, f'''[Pipeline] {drive_error_msg} — skipping upload''')
        parts = []
        if item_count:
            parts.append(f'''{item_count} items''')
        if audio_file:
            parts.append('audio generated')
        elif self.server_mode:
            parts.append('audio skipped (server)')
        else:
            parts.append('audio failed')
        if drive_uploaded:
            parts.append('uploaded to Drive')
        elif task.upload_to_drive and task.drive_folder_id:
            parts.append('Drive upload failed')
        task.last_result = f'''OK: {', '.join(parts)}'''
        if cooldown:
            pass
        self._log(task.id, f'''[Pipeline] Complete: {task.last_result}''')
        return None
    # WARNING: Decompyle incomplete

    
    def backfill_task(self = None, task_id = None, stop_flag = None, since_date = (None, None)):
        '''
        Backfill historical data for a task by crawling the archive.

        Finds the last date_published in the target sheet, then processes all
        newsletter issues from that date forward, one at a time, with dedup.

        Args:
            task_id: ID of the task to backfill
            stop_flag: Optional callable that returns True to abort mid-backfill
            since_date: Optional date string (YYYY-MM-DD) to start backfill from.
                       If provided, overrides the auto-detected since_date.
                       Use None for auto-detect (from sheet), or "" for full archive.

        Returns:
            True if started successfully
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def reenrich_task(self = None, task_id = None, stop_flag = None):
        '''Re-enrich existing sheet rows that are missing Grid data.

        Reads rows from the sheet, identifies those without grid_matched,
        runs Grid enrichment on them, and writes grid columns back.

        Args:
            task_id: The task to re-enrich
            stop_flag: Optional callable that returns True to stop

        Returns:
            True if re-enrichment started successfully.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def retitle_task(self = None, task_id = None, stop_flag = None):
        '''Re-fetch source posts and update truncated titles in the sheet.

        For Telegram tasks, paginates through all historical messages to build
        a URL→full_title map, then updates truncated sheet titles.

        Args:
            task_id: The task to re-title
            stop_flag: Optional callable that returns True to stop

        Returns:
            True if retitle started successfully.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def run_task_now(self = None, task_id = None):
        '''Manually trigger a task to run immediately.'''
        task = self.get_task(task_id)
        if task:
            threading.Thread(target = self._execute_task, args = (task,), daemon = True).start()
            return True
        return False


_scheduler: Optional[Scheduler] = None

def get_scheduler(on_task_complete = None, on_progress = None, on_task_start = None, server_mode = (None, None, None, False, None), data_dir = ('on_task_complete', Optional[Callable], 'on_progress', Optional[Callable], 'on_task_start', Optional[Callable], 'server_mode', bool, 'data_dir', Optional[str], 'return', Scheduler)):
    '''Get the global scheduler instance.'''
    pass
# WARNING: Decompyle incomplete

