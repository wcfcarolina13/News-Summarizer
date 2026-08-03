"""The per-task mutex and the watchdog's start-time map must never drift.

`_running_tasks` (the mutex) and `_running_since` (what overdue_tasks reads)
are two structures describing one fact. If a code path touches one without the
other, the watchdog either misses a hang or reports a phantom one.

When the watchdog was added (2026-08-02) only the daemon's _execute_task path
was converted; backfill_task / reenrich_task / retitle_task — the GUI's
run-now entry points — still mutated the mutex directly, so a hang triggered
from the desktop app was invisible to the watchdog.

The behavioural tests in test_task_watchdog.py can't catch that: those methods
do real network work, so they aren't callable from a unit test. This checks the
invariant structurally instead — the helpers must be the only mutators.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import scheduler as scheduler_mod

_SCHEDULER_SRC = os.path.join(os.path.dirname(__file__), '..', 'scheduler.py')
_MUTATION = re.compile(r'self\._running_tasks\.(add|discard)\(')
_HELPERS = ("_mark_running", "_unmark_running")


def _current_method(lines, idx):
    """Name of the def enclosing line index `idx`."""
    for i in range(idx, -1, -1):
        m = re.match(r'\s*def (\w+)\(', lines[i])
        if m:
            return m.group(1)
    return "<module>"


def test_running_tasks_is_only_mutated_by_the_helpers():
    with open(_SCHEDULER_SRC) as fh:
        lines = fh.read().splitlines()

    offenders = []
    for idx, line in enumerate(lines):
        if not _MUTATION.search(line):
            continue
        method = _current_method(lines, idx)
        if method not in _HELPERS:
            offenders.append(f"{method}() at scheduler.py:{idx + 1}: {line.strip()}")

    assert not offenders, (
        "these paths mutate _running_tasks directly, so _running_since drifts and "
        "the watchdog goes blind to them — use _mark_running/_unmark_running:\n  "
        + "\n  ".join(offenders)
    )


def test_helpers_exist_and_are_symmetric():
    s = scheduler_mod.Scheduler(data_dir=None)
    s._mark_running("t", "T")
    assert "t" in s._running_tasks and "t" in s._running_since
    s._unmark_running("t")
    assert "t" not in s._running_tasks and "t" not in s._running_since
