# Source Generated with Decompyle++
# File: api_usage_tracker.pyc (Python 3.12)

'''
API Usage Tracker — Centralized Gemini API call tracking and cost protection.

Thread-safe singleton that wraps every generate_content() call with:
- Pre-flight daily/monthly limit checks
- Post-call logging (model, caller, char counts, cost estimate)
- Per-scheduler-task attribution via thread-local context
- JSON persistence with lazy day/month rollover
'''
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import date, datetime
from typing import Optional, Tuple
MODEL_PRICING = {
    'gemini-2.5-flash': (0.15, 0.6),
    'gemini-2.5-pro': (1.25, 10),
    'gemini-2.0-flash': (0.1, 0.4),
    'gemini-1.5-flash': (0.075, 0.3),
    'gemini-1.5-pro': (1.25, 5) }
CHARS_PER_TOKEN = 4
MAX_LOG_ENTRIES = 500
MAX_HISTORY_DAYS = 90
_task_context = threading.local()

def set_current_task(task_id = None, task_name = None):
    '''Set the current scheduler task for the calling thread.'''
    _task_context.task_id = task_id
    _task_context.task_name = task_name


def clear_current_task():
    '''Clear the current scheduler task for the calling thread.'''
    _task_context.task_id = None
    _task_context.task_name = None


def get_current_task():
    '''Get (task_id, task_name) for the calling thread, or (None, None).'''
    return (getattr(_task_context, 'task_id', None), getattr(_task_context, 'task_name', None))


class APILimitExceeded(Exception):
    pass
# WARNING: Decompyle incomplete


class BudgetExceeded(Exception):
    pass
# WARNING: Decompyle incomplete


def _get_usage_path():
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            data_dir = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            data_dir = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            data_dir = os.path.expanduser('~/.daily-audio-briefing')
        os.makedirs(data_dir, exist_ok = True)
        return os.path.join(data_dir, 'api_usage.json')
    return None.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_usage.json')


class APIUsageTracker:
    '''Thread-safe API usage tracker with JSON persistence.'''
    
    def __init__(self):
        self._lock = threading.Lock()
        self._path = _get_usage_path()
        self._data = self._load()
        self._apply_env_overrides()

    
    def _load(self = None):
        '''Load usage data from disk, or return defaults.'''
        pass
    # WARNING: Decompyle incomplete

    _defaults = (lambda : {
'version': 1,
'limits': {
'daily_max_calls': 500,
'monthly_max_calls': 10000,
'enabled': True,
'monthly_budget_usd': 0,
'cooldown_enabled': True },
'current_period': {
'date': date.today().isoformat(),
'month': date.today().strftime('%Y-%m'),
'daily_calls': 0,
'monthly_calls': 0,
'daily_cost_estimate': 0,
'monthly_cost_estimate': 0 },
'call_log': [],
'task_totals': { },
'history': [] })()
    
    def _apply_env_overrides(self):
        '''Apply environment variable overrides for API limits.

        On Render (ephemeral filesystem), api_usage.json resets on every deploy,
        losing any budget caps or limit changes made via the UI. These env vars
        ensure limits survive redeploys:

          API_DAILY_MAX_CALLS   — Max Gemini calls per day (default 500)
          API_MONTHLY_MAX_CALLS — Max Gemini calls per month (default 10000)
          API_MONTHLY_BUDGET    — Dollar cap per month (e.g. "0.50")
          API_LIMITS_ENABLED    — "true"/"false" (default true)
          API_COOLDOWN_ENABLED  — "true"/"false" (default true)

        Env vars always win over the JSON file, so server admins can\'t
        accidentally remove protections via the UI on a fresh deploy.
        '''
        limits = self._data.setdefault('limits', { })
        val = os.environ.get('API_DAILY_MAX_CALLS')
        if val:
            limits['daily_max_calls'] = max(1, int(val))
        val = os.environ.get('API_MONTHLY_MAX_CALLS')
        if val:
            limits['monthly_max_calls'] = max(1, int(val))
        val = os.environ.get('API_MONTHLY_BUDGET')
        if val:
            limits['monthly_budget_usd'] = max(0, float(val))
        val = os.environ.get('API_LIMITS_ENABLED')
    # WARNING: Decompyle incomplete

    
    def _save(self):
        '''Atomic write to disk. Called under lock.'''
        tmp_path = self._path + '.tmp'
    # WARNING: Decompyle incomplete

    
    def _maybe_rollover(self):
        '''Reset counters at day/month boundaries. Called under lock.'''
        today_str = date.today().isoformat()
        month_str = date.today().strftime('%Y-%m')
        period = self._data.setdefault('current_period', { })
        if period.get('date') != today_str:
            if period.get('date') and period.get('daily_calls', 0) > 0:
                self._data.setdefault('history', []).append({
                    'date': period['date'],
                    'calls': period.get('daily_calls', 0),
                    'cost_estimate': round(period.get('daily_cost_estimate', 0), 6) })
                self._data['history'] = self._data['history'][-MAX_HISTORY_DAYS:]
            period['date'] = today_str
            period['daily_calls'] = 0
            period['daily_cost_estimate'] = 0
            for td in self._data.get('task_totals', { }).values():
                td['calls_today'] = 0
            if period.get('month') != month_str:
                period['month'] = month_str
                period['monthly_calls'] = 0
                period['monthly_cost_estimate'] = 0
                for td in self._data.get('task_totals', { }).values():
                    td['calls_this_month'] = 0
                return None
            return None

    _estimate_cost = (lambda model_name = None, input_chars = None, output_chars = staticmethod: pricing = Nonefor prefix, costs in MODEL_PRICING.items():
if not prefix in model_name:
continuepricing = costsMODEL_PRICING.items()if not pricing:
pricing = (0.1, 0.4)input_tokens = input_chars / CHARS_PER_TOKENoutput_tokens = output_chars / CHARS_PER_TOKENcost = input_tokens * pricing[0] / 1000000 + output_tokens * pricing[1] / 1000000round(cost, 6))()
    
    def check_limit(self = None):
        '''Return True if under daily AND monthly limits. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete

    
    def is_over_budget(self = None):
        '''Return True if monthly cost exceeds budget cap. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete

    
    def is_cooldown_active(self = None):
        '''Return True if over budget AND cooldown mode is enabled. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete

    
    def track_call(self, model_name, caller = None, input_chars = None, output_chars = None, task_id = (0, 0, None, None), task_name = ('model_name', str, 'caller', str, 'input_chars', int, 'output_chars', int, 'task_id', Optional[str], 'task_name', Optional[str])):
        '''Record an API call. Thread-safe.'''
        cost = self._estimate_cost(model_name, input_chars, output_chars)
    # WARNING: Decompyle incomplete

    
    def tracked_generate(self = None, model = None, prompt = None, caller = ('unknown', 120), timeout = ('prompt', str, 'caller', str, 'timeout', int)):
        '''Wrapper: check limit → model.generate_content(prompt) → track.

        Raises APILimitExceeded if limits are reached.
        Raises TimeoutError if the API call exceeds *timeout* seconds (default 120).
        Returns the response object from generate_content().
        '''
        (task_id, task_name) = get_current_task()
    # WARNING: Decompyle incomplete

    
    def get_stats(self = None):
        '''Return usage stats for UI display. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete

    
    def get_task_stats(self = None):
        '''Return per-task usage breakdown. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete

    
    def get_history(self = None, days = None):
        '''Return daily usage history. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete

    
    def update_limits(self, daily_max = None, monthly_max = None, enabled = None, monthly_budget_usd = (None, None, None, None, None), cooldown_enabled = ('daily_max', Optional[int], 'monthly_max', Optional[int], 'enabled', Optional[bool], 'monthly_budget_usd', Optional[float], 'cooldown_enabled', Optional[bool])):
        '''Update usage limits. Thread-safe.

        Note: env var overrides are re-applied after saving, so server-side
        limits set via API_DAILY_MAX_CALLS etc. cannot be relaxed via the UI.
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def reset_today(self):
        '''Manual reset of daily counter. Thread-safe.'''
        pass
    # WARNING: Decompyle incomplete


_tracker = None
_tracker_lock = threading.Lock()

def get_tracker():
    '''Get the global tracker instance (lazy init, thread-safe).'''
    pass
# WARNING: Decompyle incomplete

