"""
Cloud Scheduler Client — REST API wrapper for the remote scheduler on Render.

Mirrors the ServerScheduler interface so the desktop GUI can seamlessly
switch between local and cloud scheduler backends.

Usage in gui_app.py:
    from cloud_scheduler_client import CloudSchedulerClient
    client = CloudSchedulerClient("https://your-app.onrender.com")
    ok, msg = client.test_connection()
    if ok:
        tasks = client.tasks  # List[ScheduledTask]
"""

import logging
from typing import Optional, List, Tuple

import requests
from scheduler import ScheduledTask

logger = logging.getLogger(__name__)


class CloudSchedulerClient:
    """REST API client for the remote scheduler server."""

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url.rstrip('/')
        self._session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['X-API-Key'] = api_key
        self._session.headers.update(headers)
        self._cached_tasks: List[ScheduledTask] = []
        self._timeout = 8  # seconds

    # ---- Connection ----

    def test_connection(self) -> Tuple[bool, str]:
        """Test connectivity to the server. Returns (success, message)."""
        try:
            r = self._session.get(
                f"{self.server_url}/health",
                timeout=self._timeout
            )
            if r.status_code == 200:
                return True, "Connected"
            return False, f"Server returned {r.status_code}"
        except requests.ConnectionError:
            return False, "Cannot reach server"
        except requests.Timeout:
            return False, "Connection timed out"
        except Exception as e:
            return False, str(e)

    # ---- Status ----

    def get_status(self) -> dict:
        """GET /api/scheduler/status"""
        try:
            r = self._session.get(
                f"{self.server_url}/api/scheduler/status",
                timeout=self._timeout
            )
            return r.json() if r.status_code == 200 else {}
        except Exception as e:
            logger.warning(f"[CloudScheduler] get_status failed: {e}")
            return {}

    @property
    def is_running(self) -> bool:
        status = self.get_status()
        return status.get('running', False)

    # ---- Toggle ----

    def start(self):
        """POST /api/scheduler/toggle {running: true}"""
        try:
            self._session.post(
                f"{self.server_url}/api/scheduler/toggle",
                json={'running': True},
                timeout=self._timeout
            )
        except Exception as e:
            logger.warning(f"[CloudScheduler] start failed: {e}")

    def stop(self):
        """POST /api/scheduler/toggle {running: false}"""
        try:
            self._session.post(
                f"{self.server_url}/api/scheduler/toggle",
                json={'running': False},
                timeout=self._timeout
            )
        except Exception as e:
            logger.warning(f"[CloudScheduler] stop failed: {e}")

    # ---- Task CRUD ----

    @property
    def tasks(self) -> List[ScheduledTask]:
        """GET /api/scheduler/tasks — returns cached list."""
        return self._cached_tasks

    def refresh_tasks(self) -> bool:
        """Fetch tasks from server and update cache. Returns success."""
        try:
            r = self._session.get(
                f"{self.server_url}/api/scheduler/tasks",
                timeout=self._timeout
            )
            if r.status_code == 200:
                data = r.json()
                self._cached_tasks = [
                    ScheduledTask.from_dict(t) for t in data.get('tasks', [])
                ]
                return True
            return False
        except Exception as e:
            logger.warning(f"[CloudScheduler] refresh_tasks failed: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Find task by ID in cached list."""
        for t in self._cached_tasks:
            if t.id == task_id:
                return t
        return None

    def add_task(self, task: ScheduledTask) -> bool:
        """POST /api/scheduler/tasks"""
        try:
            r = self._session.post(
                f"{self.server_url}/api/scheduler/tasks",
                json=task.to_dict(),
                timeout=self._timeout
            )
            if r.status_code == 200:
                self.refresh_tasks()
                return True
            return False
        except Exception as e:
            logger.warning(f"[CloudScheduler] add_task failed: {e}")
            return False

    def update_task(self, task_id: str, updates: dict) -> bool:
        """PUT /api/scheduler/tasks/<task_id>"""
        try:
            r = self._session.put(
                f"{self.server_url}/api/scheduler/tasks/{task_id}",
                json=updates,
                timeout=self._timeout
            )
            if r.status_code == 200:
                self.refresh_tasks()
                return True
            return False
        except Exception as e:
            logger.warning(f"[CloudScheduler] update_task failed: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """DELETE /api/scheduler/tasks/<task_id>"""
        try:
            r = self._session.delete(
                f"{self.server_url}/api/scheduler/tasks/{task_id}",
                timeout=self._timeout
            )
            if r.status_code == 200:
                self.refresh_tasks()
                return True
            return False
        except Exception as e:
            logger.warning(f"[CloudScheduler] delete_task failed: {e}")
            return False

    def run_task_now(self, task_id: str) -> bool:
        """POST /api/scheduler/tasks/<task_id>/run"""
        try:
            r = self._session.post(
                f"{self.server_url}/api/scheduler/tasks/{task_id}/run",
                json={},
                timeout=self._timeout
            )
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"[CloudScheduler] run_task_now failed: {e}")
            return False
