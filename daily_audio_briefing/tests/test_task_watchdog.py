"""Regression tests for the missing task watchdog (2026-08).

Bug: when a task hung (see test_youtube_fetch_timeout.py), nothing noticed.
`_notify()` fires only from the `on_task_complete` callback, which is reached
only after a task returns or raises — a thread blocked in recv() does neither.
There was no timer, deadline or heartbeat anywhere that could observe "this
task has been running for 33 hours", so the daemon sat wedged for three days
and the outage surfaced only as an empty Drive folder.

Fix: the scheduler records when each task started; the daemon polls for tasks
that have overrun a deadline so it can notify and let launchd restart it.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scheduler import Scheduler


def _scheduler(tmp_path):
    return Scheduler(data_dir=str(tmp_path))


def test_no_overdue_tasks_when_idle(tmp_path):
    s = _scheduler(tmp_path)
    assert s.overdue_tasks(max_seconds=60) == []


def test_running_task_under_deadline_is_not_overdue(tmp_path):
    s = _scheduler(tmp_path)
    s._mark_running("task-1", "News Summarizer Pipeline")
    assert s.overdue_tasks(max_seconds=3600) == []


def test_running_task_past_deadline_is_reported(tmp_path):
    s = _scheduler(tmp_path)
    s._mark_running("task-1", "News Summarizer Pipeline")
    # Backdate the start so we don't have to actually wait.
    s._running_since["task-1"] = (time.time() - 5000, "News Summarizer Pipeline")

    overdue = s.overdue_tasks(max_seconds=3600)

    assert len(overdue) == 1
    task_id, name, elapsed = overdue[0]
    assert task_id == "task-1"
    assert name == "News Summarizer Pipeline"
    assert elapsed >= 5000


def test_finished_task_is_no_longer_overdue(tmp_path):
    s = _scheduler(tmp_path)
    s._mark_running("task-1", "News Summarizer Pipeline")
    s._running_since["task-1"] = (time.time() - 5000, "News Summarizer Pipeline")
    assert s.overdue_tasks(max_seconds=3600)

    s._unmark_running("task-1")

    assert s.overdue_tasks(max_seconds=3600) == []
    assert "task-1" not in s._running_tasks


def test_mark_running_registers_the_task_mutex_too(tmp_path):
    # The start-time map and the per-task mutex must not drift apart — that is
    # what the helpers exist to guarantee.
    s = _scheduler(tmp_path)
    s._mark_running("task-1", "Whatever")
    assert "task-1" in s._running_tasks
    assert "task-1" in s._running_since


def test_unmark_running_is_safe_for_unknown_task(tmp_path):
    s = _scheduler(tmp_path)
    s._unmark_running("never-started")  # must not raise
    assert s.overdue_tasks(max_seconds=1) == []
