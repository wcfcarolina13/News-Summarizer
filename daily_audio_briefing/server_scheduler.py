"""
Server Scheduler - Flask-integrated scheduler for cloud deployment.

Wraps the Scheduler class to run inside a Flask web process instead of
as a standalone daemon. Designed for Render.com / Railway / Fly.io free tiers
where background workers are not available.

Usage in web_app.py:
    from server_scheduler import ServerScheduler
    server_scheduler = ServerScheduler()
    server_scheduler.start()  # Call after Flask app is ready
"""

import os
import logging
from typing import Optional

from scheduler import Scheduler, ScheduledTask

logger = logging.getLogger(__name__)


class ServerScheduler:
    """Flask-compatible scheduler that runs in a background thread."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the server scheduler.

        Args:
            data_dir: Directory for config/task files. Defaults to script directory.
        """
        self.data_dir = data_dir or os.path.dirname(__file__)
        self.scheduler = Scheduler(
            on_task_complete=self._on_task_complete,
            server_mode=True,
            data_dir=self.data_dir
        )

    def _on_task_complete(self, task: ScheduledTask, success: bool, message: str):
        """Log task completion to stdout (visible in Render logs)."""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"[ServerScheduler] Task '{task.name}' {status}: {message}")

    def start(self):
        """Start the scheduler background thread."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[ServerScheduler] Started — scheduler thread is active")

    def stop(self):
        """Stop the scheduler background thread."""
        if self.scheduler.running:
            self.scheduler.stop()
            logger.info("[ServerScheduler] Stopped")

    @property
    def is_running(self) -> bool:
        return self.scheduler.running

    # --- Delegate task CRUD to the underlying scheduler ---

    @property
    def tasks(self):
        return self.scheduler.tasks

    def get_task(self, task_id: str):
        return self.scheduler.get_task(task_id)

    def add_task(self, task: ScheduledTask) -> bool:
        return self.scheduler.add_task(task)

    def update_task(self, task_id: str, updates: dict) -> bool:
        return self.scheduler.update_task(task_id, updates)

    def delete_task(self, task_id: str) -> bool:
        return self.scheduler.delete_task(task_id)

    def run_task_now(self, task_id: str) -> bool:
        return self.scheduler.run_task_now(task_id)

    def reload_tasks(self):
        """Reload tasks from disk."""
        self.scheduler.load_tasks()
