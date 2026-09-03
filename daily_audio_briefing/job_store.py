"""
job_store — JSON-on-disk records for MCP audio jobs.

One file per job under <jobs_dir>/<job_id>.json, rewritten on every change so
a restarted server (or the GUI, later) can still read status.
"""
import datetime
import json
import os
import threading
import uuid

STATES = ("queued", "running", "done", "failed")


def _now():
    return datetime.datetime.now().isoformat(timespec="microseconds")


class JobStore:
    def __init__(self, jobs_dir):
        self.jobs_dir = jobs_dir
        os.makedirs(jobs_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id):
        return os.path.join(self.jobs_dir, f"{job_id}.json")

    def _write(self, job):
        tmp = self._path(job["job_id"]) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(job, f, indent=2)
        os.replace(tmp, self._path(job["job_id"]))

    def create(self, kind, params, output_path):
        job = {
            "job_id": uuid.uuid4().hex[:12],
            "kind": kind,
            "state": "queued",
            "params": params,
            "progress": "",
            "output_path": output_path,
            "error": None,
            "created": _now(),
            "finished": None,
        }
        with self._lock:
            self._write(job)
        return job

    def get(self, job_id):
        path = self._path(job_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, OSError):
            return None

    def update(self, job_id, **fields):
        if "state" in fields and fields["state"] not in STATES:
            raise ValueError(f"bad state {fields['state']!r}")
        with self._lock:
            job = self.get(job_id)
            if job is None:
                raise KeyError(job_id)
            job.update(fields)
            if fields.get("state") in ("done", "failed"):
                job["finished"] = _now()
            self._write(job)
        return job

    def list(self, limit=20):
        jobs = []
        for name in os.listdir(self.jobs_dir):
            if name.endswith(".json"):
                job = self.get(name[:-5])
                if job:
                    jobs.append(job)
        jobs.sort(key=lambda j: j["created"], reverse=True)
        return jobs[:limit]

    def recover_interrupted(self):
        count = 0
        for job in self.list(limit=10_000):
            if job["state"] in ("queued", "running"):
                self.update(job["job_id"], state="failed", error="server restarted")
                count += 1
        return count
