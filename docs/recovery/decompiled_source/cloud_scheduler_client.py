# Source Generated with Decompyle++
# File: cloud_scheduler_client.pyc (Python 3.12)

'''
Cloud Scheduler Client — REST API wrapper for the remote scheduler on Render.

Mirrors the ServerScheduler interface so the desktop GUI can seamlessly
switch between local and cloud scheduler backends.

Usage in gui_app.py:
    from cloud_scheduler_client import CloudSchedulerClient
    client = CloudSchedulerClient("https://your-app.onrender.com")
    ok, msg = client.test_connection()
    if ok:
        tasks = client.tasks  # List[ScheduledTask]
'''
import logging
from typing import Optional, List, Tuple
import requests
from scheduler import ScheduledTask
logger = logging.getLogger(__name__)

class CloudSchedulerClient:
    '''REST API client for the remote scheduler server.'''
    
    def __init__(self = None, server_url = None, api_key = None):
        self.server_url = server_url.rstrip('/')
        self._session = requests.Session()
        headers = {
            'Content-Type': 'application/json' }
        if api_key:
            headers['X-API-Key'] = api_key
        self._session.headers.update(headers)
        self._cached_tasks = []
        self._timeout = 8

    
    def test_connection(self = None):
        '''Test connectivity to the server. Returns (success, message).'''
        r = self._session.get(f'''{self.server_url}/health''', timeout = self._timeout)
        if r.status_code == 200:
            return (True, 'Connected')
        return (False, f'''Server returned {r.status_code}''')
    # WARNING: Decompyle incomplete

    
    def get_status(self = None):
        '''GET /api/scheduler/status'''
        r = self._session.get(f'''{self.server_url}/api/scheduler/status''', timeout = self._timeout)
        if r.status_code == 200:
            return r.json()
        return None
    # WARNING: Decompyle incomplete

    is_running = (lambda self = None: status = self.get_status()status.get('running', False))()
    
    def start(self):
        '''POST /api/scheduler/toggle {running: true}'''
        self._session.post(f'''{self.server_url}/api/scheduler/toggle''', json = {
            'running': True }, timeout = self._timeout)
        return None
    # WARNING: Decompyle incomplete

    
    def stop(self):
        '''POST /api/scheduler/toggle {running: false}'''
        self._session.post(f'''{self.server_url}/api/scheduler/toggle''', json = {
            'running': False }, timeout = self._timeout)
        return None
    # WARNING: Decompyle incomplete

    tasks = (lambda self = None: self._cached_tasks)()
    
    def refresh_tasks(self = None):
        '''Fetch tasks from server and update cache. Returns success.'''
        r = self._session.get(f'''{self.server_url}/api/scheduler/tasks''', timeout = self._timeout)
    # WARNING: Decompyle incomplete

    
    def get_task(self = None, task_id = None):
        '''Find task by ID in cached list.'''
        for t in self._cached_tasks:
            if not t.id == task_id:
                continue
            
            return self._cached_tasks, t

    
    def add_task(self = None, task = None):
        '''POST /api/scheduler/tasks'''
        r = self._session.post(f'''{self.server_url}/api/scheduler/tasks''', json = task.to_dict(), timeout = self._timeout)
        if r.status_code == 200:
            self.refresh_tasks()
            return True
        return False
    # WARNING: Decompyle incomplete

    
    def update_task(self = None, task_id = None, updates = None):
        '''PUT /api/scheduler/tasks/<task_id>'''
        r = self._session.put(f'''{self.server_url}/api/scheduler/tasks/{task_id}''', json = updates, timeout = self._timeout)
        if r.status_code == 200:
            self.refresh_tasks()
            return True
        return False
    # WARNING: Decompyle incomplete

    
    def delete_task(self = None, task_id = None):
        '''DELETE /api/scheduler/tasks/<task_id>'''
        r = self._session.delete(f'''{self.server_url}/api/scheduler/tasks/{task_id}''', timeout = self._timeout)
        if r.status_code == 200:
            self.refresh_tasks()
            return True
        return False
    # WARNING: Decompyle incomplete

    
    def run_task_now(self = None, task_id = None):
        '''POST /api/scheduler/tasks/<task_id>/run'''
        r = self._session.post(f'''{self.server_url}/api/scheduler/tasks/{task_id}/run''', json = { }, timeout = self._timeout)
        return r.status_code == 200
    # WARNING: Decompyle incomplete


