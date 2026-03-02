"""
API Usage Tracker — Centralized Gemini API call tracking and cost protection.

Thread-safe singleton that wraps every generate_content() call with:
- Pre-flight daily/monthly limit checks
- Post-call logging (model, caller, char counts, cost estimate)
- Per-scheduler-task attribution via thread-local context
- JSON persistence with lazy day/month rollover
"""

import json
import os
import sys
import threading
from datetime import date, datetime
from typing import Optional, Tuple

# Gemini pricing (input $/1M tokens, output $/1M tokens)
MODEL_PRICING = {
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
}
CHARS_PER_TOKEN = 4  # rough approximation
MAX_LOG_ENTRIES = 500
MAX_HISTORY_DAYS = 90


# ---------------------------------------------------------------------------
# Thread-local task context (set by scheduler, read by tracked_generate)
# ---------------------------------------------------------------------------
_task_context = threading.local()


def set_current_task(task_id: str, task_name: str):
    """Set the current scheduler task for the calling thread."""
    _task_context.task_id = task_id
    _task_context.task_name = task_name


def clear_current_task():
    """Clear the current scheduler task for the calling thread."""
    _task_context.task_id = None
    _task_context.task_name = None


def get_current_task() -> Tuple[Optional[str], Optional[str]]:
    """Get (task_id, task_name) for the calling thread, or (None, None)."""
    return (
        getattr(_task_context, "task_id", None),
        getattr(_task_context, "task_name", None),
    )


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------
class APILimitExceeded(Exception):
    """Raised when an API call would exceed configured limits."""

    def __init__(self, limit_type: str, current: int, maximum: int):
        self.limit_type = limit_type
        self.current = current
        self.maximum = maximum
        super().__init__(f"API {limit_type} limit reached: {current}/{maximum}")


class BudgetExceeded(Exception):
    """Raised when an API call would exceed the configured dollar budget."""

    def __init__(self, current_cost: float, budget_cap: float):
        self.current_cost = current_cost
        self.budget_cap = budget_cap
        super().__init__(
            f"Monthly budget exceeded: ${current_cost:.4f} / ${budget_cap:.2f}"
        )


# ---------------------------------------------------------------------------
# Path helper (mirrors get_data_directory() used across the project)
# ---------------------------------------------------------------------------
def _get_usage_path() -> str:
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            data_dir = os.path.expanduser(
                "~/Library/Application Support/Daily Audio Briefing"
            )
        elif sys.platform == "win32":
            data_dir = os.path.join(
                os.environ.get("APPDATA", ""), "Daily Audio Briefing"
            )
        else:
            data_dir = os.path.expanduser("~/.daily-audio-briefing")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "api_usage.json")
    else:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "api_usage.json"
        )


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------
class APIUsageTracker:
    """Thread-safe API usage tracker with JSON persistence."""

    def __init__(self):
        self._lock = threading.Lock()
        self._path = _get_usage_path()
        self._data = self._load()
        self._apply_env_overrides()

    # --- Persistence ---

    def _load(self) -> dict:
        """Load usage data from disk, or return defaults."""
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data.get("version") == 1:
                        return data
        except (json.JSONDecodeError, OSError) as e:
            print(f"[APITracker] Warning: Could not load {self._path}: {e}")
        return self._defaults()

    @staticmethod
    def _defaults() -> dict:
        return {
            "version": 1,
            "limits": {
                "daily_max_calls": 500,
                "monthly_max_calls": 10000,
                "enabled": True,
                "monthly_budget_usd": 0.0,
                "cooldown_enabled": True,
            },
            "current_period": {
                "date": date.today().isoformat(),
                "month": date.today().strftime("%Y-%m"),
                "daily_calls": 0,
                "monthly_calls": 0,
                "daily_cost_estimate": 0.0,
                "monthly_cost_estimate": 0.0,
            },
            "call_log": [],
            "task_totals": {},
            "history": [],
        }

    def _apply_env_overrides(self):
        """Apply environment variable overrides for API limits.

        On Render (ephemeral filesystem), api_usage.json resets on every deploy,
        losing any budget caps or limit changes made via the UI. These env vars
        ensure limits survive redeploys:

          API_DAILY_MAX_CALLS   — Max Gemini calls per day (default 500)
          API_MONTHLY_MAX_CALLS — Max Gemini calls per month (default 10000)
          API_MONTHLY_BUDGET    — Dollar cap per month (e.g. "0.50")
          API_LIMITS_ENABLED    — "true"/"false" (default true)
          API_COOLDOWN_ENABLED  — "true"/"false" (default true)

        Env vars always win over the JSON file, so server admins can't
        accidentally remove protections via the UI on a fresh deploy.
        """
        limits = self._data.setdefault("limits", {})

        val = os.environ.get("API_DAILY_MAX_CALLS")
        if val:
            try:
                limits["daily_max_calls"] = max(1, int(val))
            except ValueError:
                pass

        val = os.environ.get("API_MONTHLY_MAX_CALLS")
        if val:
            try:
                limits["monthly_max_calls"] = max(1, int(val))
            except ValueError:
                pass

        val = os.environ.get("API_MONTHLY_BUDGET")
        if val:
            try:
                limits["monthly_budget_usd"] = max(0.0, float(val))
            except ValueError:
                pass

        val = os.environ.get("API_LIMITS_ENABLED")
        if val is not None:
            limits["enabled"] = val.lower() in ("true", "1", "yes")

        val = os.environ.get("API_COOLDOWN_ENABLED")
        if val is not None:
            limits["cooldown_enabled"] = val.lower() in ("true", "1", "yes")

    def _save(self):
        """Atomic write to disk. Called under lock."""
        try:
            tmp_path = self._path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            os.replace(tmp_path, self._path)
        except OSError as e:
            print(f"[APITracker] Warning: Could not save usage data: {e}")

    # --- Rollover ---

    def _maybe_rollover(self):
        """Reset counters at day/month boundaries. Called under lock."""
        today_str = date.today().isoformat()
        month_str = date.today().strftime("%Y-%m")
        period = self._data.setdefault("current_period", {})

        if period.get("date") != today_str:
            # Archive yesterday to history
            if period.get("date") and period.get("daily_calls", 0) > 0:
                self._data.setdefault("history", []).append(
                    {
                        "date": period["date"],
                        "calls": period.get("daily_calls", 0),
                        "cost_estimate": round(
                            period.get("daily_cost_estimate", 0), 6
                        ),
                    }
                )
                # Trim history
                self._data["history"] = self._data["history"][-MAX_HISTORY_DAYS:]

            # Reset daily
            period["date"] = today_str
            period["daily_calls"] = 0
            period["daily_cost_estimate"] = 0.0

            # Reset per-task daily counters
            for td in self._data.get("task_totals", {}).values():
                td["calls_today"] = 0

            # Monthly rollover
            if period.get("month") != month_str:
                period["month"] = month_str
                period["monthly_calls"] = 0
                period["monthly_cost_estimate"] = 0.0
                for td in self._data.get("task_totals", {}).values():
                    td["calls_this_month"] = 0

    # --- Cost estimation ---

    @staticmethod
    def _estimate_cost(model_name: str, input_chars: int, output_chars: int) -> float:
        pricing = None
        for prefix, costs in MODEL_PRICING.items():
            if prefix in model_name:
                pricing = costs
                break
        if not pricing:
            pricing = (0.10, 0.40)  # Default to flash pricing

        input_tokens = input_chars / CHARS_PER_TOKEN
        output_tokens = output_chars / CHARS_PER_TOKEN
        cost = (input_tokens * pricing[0] / 1_000_000) + (
            output_tokens * pricing[1] / 1_000_000
        )
        return round(cost, 6)

    # --- Core API ---

    def check_limit(self) -> bool:
        """Return True if under daily AND monthly limits. Thread-safe."""
        with self._lock:
            self._maybe_rollover()
            limits = self._data.get("limits", {})
            if not limits.get("enabled", True):
                return True
            period = self._data.get("current_period", {})
            daily = period.get("daily_calls", 0)
            monthly = period.get("monthly_calls", 0)
            daily_max = limits.get("daily_max_calls", 500)
            monthly_max = limits.get("monthly_max_calls", 10000)
            return daily < daily_max and monthly < monthly_max

    def is_over_budget(self) -> bool:
        """Return True if monthly cost exceeds budget cap. Thread-safe."""
        with self._lock:
            self._maybe_rollover()
            limits = self._data.get("limits", {})
            budget = limits.get("monthly_budget_usd", 0)
            if budget <= 0:
                return False
            cost = self._data.get("current_period", {}).get(
                "monthly_cost_estimate", 0
            )
            return cost >= budget

    def is_cooldown_active(self) -> bool:
        """Return True if over budget AND cooldown mode is enabled. Thread-safe."""
        with self._lock:
            self._maybe_rollover()
            limits = self._data.get("limits", {})
            if not limits.get("cooldown_enabled", True):
                return False
            budget = limits.get("monthly_budget_usd", 0)
            if budget <= 0:
                return False
            cost = self._data.get("current_period", {}).get(
                "monthly_cost_estimate", 0
            )
            return cost >= budget

    def track_call(
        self,
        model_name: str,
        caller: str,
        input_chars: int = 0,
        output_chars: int = 0,
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
    ):
        """Record an API call. Thread-safe."""
        cost = self._estimate_cost(model_name, input_chars, output_chars)

        with self._lock:
            self._maybe_rollover()
            period = self._data["current_period"]

            # Update counters
            period["daily_calls"] = period.get("daily_calls", 0) + 1
            period["monthly_calls"] = period.get("monthly_calls", 0) + 1
            period["daily_cost_estimate"] = round(
                period.get("daily_cost_estimate", 0) + cost, 6
            )
            period["monthly_cost_estimate"] = round(
                period.get("monthly_cost_estimate", 0) + cost, 6
            )

            # Append to call log
            log_entry = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "model": model_name,
                "caller": caller,
                "input_chars": input_chars,
                "output_chars": output_chars,
                "estimated_cost": cost,
            }
            if task_id:
                log_entry["task_id"] = task_id
            self._data.setdefault("call_log", []).append(log_entry)
            # Prune oldest entries
            if len(self._data["call_log"]) > MAX_LOG_ENTRIES:
                self._data["call_log"] = self._data["call_log"][-MAX_LOG_ENTRIES:]

            # Update per-task totals
            if task_id:
                totals = self._data.setdefault("task_totals", {})
                if task_id not in totals:
                    totals[task_id] = {
                        "name": task_name or "Unknown",
                        "calls_today": 0,
                        "calls_this_month": 0,
                    }
                totals[task_id]["calls_today"] = (
                    totals[task_id].get("calls_today", 0) + 1
                )
                totals[task_id]["calls_this_month"] = (
                    totals[task_id].get("calls_this_month", 0) + 1
                )
                totals[task_id]["last_run"] = datetime.now().isoformat(
                    timespec="seconds"
                )

            self._save()

    def tracked_generate(self, model, prompt: str, caller: str = "unknown"):
        """Wrapper: check limit → model.generate_content(prompt) → track.

        Raises APILimitExceeded if limits are reached.
        Returns the response object from generate_content().
        """
        # Auto-detect task context from thread-local
        task_id, task_name = get_current_task()

        # Pre-flight limit check
        with self._lock:
            self._maybe_rollover()
            limits = self._data.get("limits", {})
            if limits.get("enabled", True):
                period = self._data.get("current_period", {})
                daily = period.get("daily_calls", 0)
                monthly = period.get("monthly_calls", 0)
                daily_max = limits.get("daily_max_calls", 500)
                monthly_max = limits.get("monthly_max_calls", 10000)
                if daily >= daily_max:
                    raise APILimitExceeded("daily", daily, daily_max)
                if monthly >= monthly_max:
                    raise APILimitExceeded("monthly", monthly, monthly_max)

                # Dollar-based budget cap
                budget_cap = limits.get("monthly_budget_usd", 0)
                if budget_cap > 0 and limits.get("cooldown_enabled", True):
                    monthly_cost = period.get("monthly_cost_estimate", 0)
                    if monthly_cost >= budget_cap:
                        raise BudgetExceeded(monthly_cost, budget_cap)

        # Make the actual API call (outside lock)
        response = model.generate_content(prompt)

        # Extract model name
        model_name = (
            getattr(model, "_model_name", None)
            or getattr(model, "model_name", None)
            or "unknown"
        )
        # Clean up model name (may have "models/" prefix)
        if isinstance(model_name, str) and model_name.startswith("models/"):
            model_name = model_name[len("models/"):]

        input_chars = len(prompt) if isinstance(prompt, str) else 0
        output_chars = len(response.text) if hasattr(response, "text") and response.text else 0

        self.track_call(model_name, caller, input_chars, output_chars, task_id, task_name)
        return response

    # --- Stats for UI ---

    def get_stats(self) -> dict:
        """Return usage stats for UI display. Thread-safe."""
        with self._lock:
            self._maybe_rollover()
            period = self._data.get("current_period", {})
            limits = self._data.get("limits", {})
            return {
                "daily_calls": period.get("daily_calls", 0),
                "monthly_calls": period.get("monthly_calls", 0),
                "daily_cost_estimate": period.get("daily_cost_estimate", 0),
                "monthly_cost_estimate": period.get("monthly_cost_estimate", 0),
                "daily_limit": limits.get("daily_max_calls", 500),
                "monthly_limit": limits.get("monthly_max_calls", 10000),
                "limits_enabled": limits.get("enabled", True),
                "monthly_budget_usd": limits.get("monthly_budget_usd", 0),
                "cooldown_enabled": limits.get("cooldown_enabled", True),
                "date": period.get("date", ""),
                "month": period.get("month", ""),
            }

    def get_task_stats(self) -> dict:
        """Return per-task usage breakdown. Thread-safe."""
        with self._lock:
            self._maybe_rollover()
            return dict(self._data.get("task_totals", {}))

    def get_history(self, days: int = 30) -> list:
        """Return daily usage history. Thread-safe."""
        with self._lock:
            history = self._data.get("history", [])
            return history[-days:]

    # --- Config ---

    def update_limits(
        self,
        daily_max: Optional[int] = None,
        monthly_max: Optional[int] = None,
        enabled: Optional[bool] = None,
        monthly_budget_usd: Optional[float] = None,
        cooldown_enabled: Optional[bool] = None,
    ):
        """Update usage limits. Thread-safe.

        Note: env var overrides are re-applied after saving, so server-side
        limits set via API_DAILY_MAX_CALLS etc. cannot be relaxed via the UI.
        """
        with self._lock:
            limits = self._data.setdefault("limits", {})
            if daily_max is not None:
                limits["daily_max_calls"] = max(1, int(daily_max))
            if monthly_max is not None:
                limits["monthly_max_calls"] = max(1, int(monthly_max))
            if enabled is not None:
                limits["enabled"] = bool(enabled)
            if monthly_budget_usd is not None:
                limits["monthly_budget_usd"] = max(0.0, float(monthly_budget_usd))
            if cooldown_enabled is not None:
                limits["cooldown_enabled"] = bool(cooldown_enabled)
            self._save()
            # Re-apply env overrides so server-side protections can't be relaxed via UI
            self._apply_env_overrides()

    def reset_today(self):
        """Manual reset of daily counter. Thread-safe."""
        with self._lock:
            period = self._data.get("current_period", {})
            period["daily_calls"] = 0
            period["daily_cost_estimate"] = 0.0
            for td in self._data.get("task_totals", {}).values():
                td["calls_today"] = 0
            self._save()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_tracker = None
_tracker_lock = threading.Lock()


def get_tracker() -> APIUsageTracker:
    """Get the global tracker instance (lazy init, thread-safe)."""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = APIUsageTracker()
    return _tracker
