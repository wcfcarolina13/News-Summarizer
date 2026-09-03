import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from job_store import JobStore, STATES  # noqa: E402


def test_create_and_get(tmp_path):
    store = JobStore(str(tmp_path / "jobs"))
    job = store.create("text_to_audio", {"voice": "af_sarah"}, "/tmp/out.wav")
    assert job["state"] == "queued" and job["kind"] == "text_to_audio"
    assert job["job_id"] and job["created"] and job["finished"] is None
    on_disk = json.load(open(tmp_path / "jobs" / f"{job['job_id']}.json"))
    assert on_disk == job
    assert store.get(job["job_id"]) == job
    assert store.get("missing") is None


def test_update_persists_and_sets_finished(tmp_path):
    store = JobStore(str(tmp_path))
    job = store.create("urls_to_audio", {}, None)
    store.update(job["job_id"], state="running", progress="[1/5] Fetching")
    assert store.get(job["job_id"])["progress"] == "[1/5] Fetching"
    done = store.update(job["job_id"], state="done", output_path="/x.mp3")
    assert done["finished"] is not None and done["output_path"] == "/x.mp3"


def test_update_rejects_bad_state(tmp_path):
    import pytest
    store = JobStore(str(tmp_path))
    job = store.create("text_to_audio", {}, None)
    with pytest.raises(ValueError):
        store.update(job["job_id"], state="exploded")


def test_list_newest_first_with_limit(tmp_path):
    store = JobStore(str(tmp_path))
    ids = []
    for _ in range(3):
        ids.append(store.create("text_to_audio", {}, None)["job_id"])
        time.sleep(0.01)
    listed = store.list(limit=2)
    assert [j["job_id"] for j in listed] == ids[::-1][:2]


def test_recover_interrupted(tmp_path):
    store = JobStore(str(tmp_path))
    a = store.create("text_to_audio", {}, None)
    b = store.create("text_to_audio", {}, None)
    store.update(a["job_id"], state="running")
    # Simulate a's owning process no longer existing (e.g. server restarted).
    store.update(a["job_id"], pid=999999)
    store.update(b["job_id"], state="done")
    assert store.recover_interrupted() == 1
    assert store.get(a["job_id"])["state"] == "failed"
    assert store.get(a["job_id"])["error"] == "server restarted"
    assert store.get(b["job_id"])["state"] == "done"


def test_states_constant():
    assert STATES == ("queued", "running", "done", "failed")


def test_list_and_recover_skip_corrupt_file(tmp_path):
    store = JobStore(str(tmp_path))
    job = store.create("text_to_audio", {}, None)
    store.update(job["job_id"], pid=999999)  # simulate a dead owning process
    with open(tmp_path / "bad.json", "w", encoding="utf-8") as f:
        f.write("{not valid json")
    listed = store.list()
    assert [j["job_id"] for j in listed] == [job["job_id"]]
    assert store.recover_interrupted() == 1
    assert store.get(job["job_id"])["state"] == "failed"


def test_list_and_recover_tolerate_non_job_json(tmp_path):
    store = JobStore(str(tmp_path / "jobs"))
    real = store.create("text_to_audio", {}, None)
    store.update(real["job_id"], pid=999999)  # simulate a dead owning process
    with open(os.path.join(store.jobs_dir, "weird.json"), "w") as f:
        f.write("{}")
    ids = [j["job_id"] for j in store.list()]
    assert ids == [real["job_id"]]
    assert store.get("weird") is None
    assert store.recover_interrupted() == 1


def test_recover_skips_jobs_owned_by_live_pid(tmp_path):
    store = JobStore(str(tmp_path))
    job = store.create("text_to_audio", {}, None)
    store.update(job["job_id"], state="running")
    assert store.get(job["job_id"])["pid"] == os.getpid()
    assert store.recover_interrupted() == 0
    assert store.get(job["job_id"])["state"] == "running"


def test_recover_marks_jobs_with_dead_pid(tmp_path):
    store = JobStore(str(tmp_path))
    job = store.create("text_to_audio", {}, None)
    store.update(job["job_id"], state="running")
    path = os.path.join(store.jobs_dir, f"{job['job_id']}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["pid"] = 999999
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    assert store.recover_interrupted() == 1
    recovered = store.get(job["job_id"])
    assert recovered["state"] == "failed"
    assert recovered["error"] == "server restarted"


def test_recover_marks_jobs_without_pid(tmp_path):
    store = JobStore(str(tmp_path))
    job_id = "legacy1234ab"
    path = os.path.join(str(tmp_path), f"{job_id}.json")
    legacy = {
        "job_id": job_id,
        "kind": "text_to_audio",
        "state": "running",
        "params": {},
        "progress": "",
        "output_path": None,
        "error": None,
        "created": "2026-01-01T00:00:00.000000",
        "finished": None,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(legacy, f)
    assert store.recover_interrupted() == 1
    recovered = store.get(job_id)
    assert recovered["state"] == "failed"
    assert recovered["error"] == "server restarted"


def test_pid_alive_helper():
    from job_store import _pid_alive
    assert _pid_alive(os.getpid()) is True
    assert _pid_alive(999999) is False
    assert _pid_alive(None) is False
