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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import date, datetime
from typing import Optional, Tuple

# Gemini pricing (input $/1M tokens, output $/1M tokens)
# Note: Gemini 2.5 models use "thinking" tokens internally which are billed
# at output token rates but NOT visible in the response text. The thinking
# multiplier below accounts for this hidden cost.
MODEL_PRICING = {
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
}
CHARS_PER_TOKEN = 4  # rough approximation
# Gemini 2.5 models generate ~3-8x more tokens internally for "thinking"
# than they return as visible output. This multiplier adjusts cost estimates.
THINKING_TOKEN_MULTIPLIER = 5

# ---------------------------------------------------------------------------
# Free tier rate limits (Google AI Studio, per-key)
# These are enforced regardless of the user's budget settings to ensure
# the app stays within the free tier and never triggers billing.
# Source: https://ai.google.dev/pricing
# ---------------------------------------------------------------------------
FREE_TIER_LIMITS = {
    "gemini-2.5-flash": {"rpm": 10, "rpd": 500},   # conservative vs 15/1500
    "gemini-2.5-pro":   {"rpm": 5,  "rpd": 50},
    "gemini-2.0-flash": {"rpm": 10, "rpd": 1000},
    "gemini-1.5-flash": {"rpm": 10, "rpd": 1000},
    "gemini-1.5-pro":   {"rpm": 2,  "rpd": 50},
}
# Default fallback if model not in table
FREE_TIER_DEFAULT = {"rpm": 5, "rpd": 100}
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
class FreeTierExceeded(Exception):
    """Raised when a call would exceed free tier rate limits."""

    def __init__(self, limit_type: str, current: int, maximum: int):
        self.limit_type = limit_type
        self.current = current
        self.maximum = maximum
        super().__init__(f"Free tier {limit_type} limit: {current}/{maximum}")


class APIUsageTracker:
    """Thread-safe API usage tracker with JSON persistence."""

    def __init__(self):
        self._lock = threading.Lock()
        self._path = _get_usage_path()
        # Per-minute call timestamps for RPM enforcement (in-memory only)
        self._recent_calls: list = []  # list of datetime
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
                "free_tier_only": True,
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
          API_MONTHLY_BUDGET    — Dollar cap per month. 0 means zero spend
                                   allowed (every call falls through to Groq).
                                   Set API_COOLDOWN_ENABLED=false to disable
                                   the dollar cap entirely.
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

        val = os.environ.get("API_FREE_TIER_ONLY")
        if val is not None:
            limits["free_tier_only"] = val.lower() in ("true", "1", "yes")

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

        # Gemini 2.5 models use hidden "thinking" tokens billed at output rates.
        # These aren't in the response text, so we apply a multiplier.
        thinking_multiplier = 1
        if "2.5" in model_name:
            thinking_multiplier = THINKING_TOKEN_MULTIPLIER

        cost = (input_tokens * pricing[0] / 1_000_000) + (
            output_tokens * thinking_multiplier * pricing[1] / 1_000_000
        )
        return round(cost, 6)

    # --- Free tier enforcement ---

    def _get_free_tier_limits(self, model) -> dict:
        """Get RPM/RPD limits for the given model."""
        model_name = (
            getattr(model, "_model_name", None)
            or getattr(model, "model_name", None)
            or "unknown"
        )
        if isinstance(model_name, str) and model_name.startswith("models/"):
            model_name = model_name[len("models/"):]
        for prefix, limits in FREE_TIER_LIMITS.items():
            if prefix in str(model_name):
                return limits
        return FREE_TIER_DEFAULT

    def _enforce_free_tier(self, model):
        """Check RPM and RPD against free tier limits. Must be called under lock.

        Raises FreeTierExceeded if the call would exceed free tier limits.
        """
        now = datetime.now()
        ft = self._get_free_tier_limits(model)

        # RPM check — count calls in the last 60 seconds
        one_minute_ago = now.timestamp() - 60
        self._recent_calls = [t for t in self._recent_calls if t > one_minute_ago]
        if len(self._recent_calls) >= ft["rpm"]:
            raise FreeTierExceeded("rpm", len(self._recent_calls), ft["rpm"])

        # RPD check — use daily_calls from persisted data
        period = self._data.get("current_period", {})
        daily = period.get("daily_calls", 0)
        if daily >= ft["rpd"]:
            raise FreeTierExceeded("rpd", daily, ft["rpd"])

        # Record this call timestamp for RPM tracking
        self._recent_calls.append(now.timestamp())

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
        """Return True if monthly cost is at or above the budget cap.

        budget == 0 means "spend zero dollars" — always over budget so the
        fallback chain takes every call. To opt out of the dollar cap entirely,
        set ``cooldown_enabled`` to False (this method ignores that flag; use
        ``is_cooldown_active`` for the user-facing gate).
        """
        with self._lock:
            self._maybe_rollover()
            limits = self._data.get("limits", {})
            budget = limits.get("monthly_budget_usd", 0)
            cost = self._data.get("current_period", {}).get(
                "monthly_cost_estimate", 0
            )
            return cost >= budget

    def is_cooldown_active(self) -> bool:
        """Return True when Gemini should be skipped in favor of the fallback.

        Active when ``cooldown_enabled`` is True and monthly cost is at or above
        ``monthly_budget_usd``. A budget of 0 keeps cooldown permanently active.
        """
        with self._lock:
            self._maybe_rollover()
            limits = self._data.get("limits", {})
            if not limits.get("cooldown_enabled", True):
                return False
            budget = limits.get("monthly_budget_usd", 0)
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

    def tracked_generate(self, model, prompt: str, caller: str = "unknown", timeout: int = 120):
        """Wrapper: check limit → model.generate_content(prompt) → track.

        Raises APILimitExceeded if limits are reached.
        Raises TimeoutError if the API call exceeds *timeout* seconds (default 120).
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

                # Dollar-based budget cap. budget == 0 with cooldown enabled
                # means "spend nothing" — every call raises so the fallback
                # chain (Groq) handles it. Set cooldown_enabled to False to
                # disable the dollar cap entirely.
                if limits.get("cooldown_enabled", True):
                    budget_cap = limits.get("monthly_budget_usd", 0)
                    monthly_cost = period.get("monthly_cost_estimate", 0)
                    if monthly_cost >= budget_cap:
                        raise BudgetExceeded(monthly_cost, budget_cap)

            # Free tier rate limiting — enforced regardless of other limits.
            # Keeps usage within Google AI Studio's free tier to avoid billing.
            if limits.get("free_tier_only", True):
                self._enforce_free_tier(model)

        # Sleep outside lock if we're close to RPM to space out calls
        import time
        time.sleep(0.5)  # small delay between calls to stay well under RPM

        # Make the actual API call (outside lock) with timeout guard
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(model.generate_content, prompt)
            try:
                response = future.result(timeout=timeout)
            except FuturesTimeoutError:
                raise TimeoutError(
                    f"API call timed out after {timeout}s (caller={caller})"
                )

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
