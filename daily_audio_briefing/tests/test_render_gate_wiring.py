"""Tests for the deferred-render wiring in scheduler.py.

Covers the sidecar "pending_render.json" manifest that carries a GPU-deferred
render's processed-videos + voiced-note commits across runs, so a briefing that is
fetched now but rendered later (once the GPU frees up) doesn't re-fetch/re-voice the
same content on the next day. Also covers the short-retry time helper.

These test the manifest helpers directly (a full _execute_pipeline_task run needs
network + Kokoro). The gate decision itself is covered by test_briefing_gate.py.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import scheduler as scheduler_mod
from scheduler import Scheduler
from video_cache import load_cache


def _bare_scheduler():
    """A Scheduler with no __init__ side effects (no Sheets/tasks loading)."""
    s = Scheduler.__new__(Scheduler)
    s._on_progress = None
    s.server_mode = False
    return s


class _FakeFetcher:
    def __init__(self, ids):
        self._ids = list(ids)

    def stash_pending_cache(self):
        return list(self._ids)


class _Note:
    def __init__(self, path):
        self.metadata = {"origin": "local_markdown", "path": path}


def test_calculate_retry_run_is_soon(monkeypatch):
    s = _bare_scheduler()
    out = s._calculate_retry_run(15)
    delta = dt.datetime.fromisoformat(out) - dt.datetime.now()
    assert dt.timedelta(minutes=14) < delta <= dt.timedelta(minutes=15)


def test_calculate_retry_run_bad_value_defaults():
    s = _bare_scheduler()
    out = s._calculate_retry_run("nonsense")
    delta = dt.datetime.fromisoformat(out) - dt.datetime.now()
    assert delta <= dt.timedelta(minutes=15)


def test_manifest_write_then_commit(tmp_path):
    s = _bare_scheduler()
    data_dir = str(tmp_path)
    today = dt.date(2026, 7, 12)

    s._pipeline_write_render_manifest(
        data_dir, today, _FakeFetcher(["vidA", "vidB"]), [_Note("/n/one.md")]
    )
    mpath = os.path.join(data_dir, "pending_render.json")
    assert os.path.exists(mpath)
    m = json.load(open(mpath))
    assert m["date"] == "2026-07-12"
    assert m["video_ids"] == ["vidA", "vidB"]
    assert m["note_paths"] == ["/n/one.md"]

    # Commit for the same day → caches updated, manifest removed.
    v, n = s._pipeline_commit_render_manifest(data_dir, today)
    assert (v, n) == (2, 1)
    assert not os.path.exists(mpath)

    cache = load_cache(data_dir)
    assert "vidA" in cache["videos"] and "vidB" in cache["videos"]
    voiced = json.load(open(os.path.join(data_dir, "voiced_newsletter_notes.json")))
    assert "/n/one.md" in voiced["paths"]


def test_manifest_commit_is_date_guarded(tmp_path):
    """A manifest from a previous day must NOT stamp today's caches; just cleaned."""
    s = _bare_scheduler()
    data_dir = str(tmp_path)
    yesterday = dt.date(2026, 7, 11)

    s._pipeline_write_render_manifest(data_dir, yesterday, _FakeFetcher(["stale"]), [])
    v, n = s._pipeline_commit_render_manifest(data_dir, dt.date(2026, 7, 12))
    assert (v, n) == (0, 0)  # not committed
    assert not os.path.exists(os.path.join(data_dir, "pending_render.json"))  # cleaned
    assert "stale" not in load_cache(data_dir).get("videos", {})


def test_manifest_commit_noop_when_absent(tmp_path):
    s = _bare_scheduler()
    assert s._pipeline_commit_render_manifest(str(tmp_path), dt.date(2026, 7, 12)) == (0, 0)


def test_discard_manifest(tmp_path):
    s = _bare_scheduler()
    data_dir = str(tmp_path)
    s._pipeline_write_render_manifest(data_dir, dt.date(2026, 7, 12), _FakeFetcher(["x"]), [])
    assert os.path.exists(os.path.join(data_dir, "pending_render.json"))
    s._pipeline_discard_render_manifest(data_dir)
    assert not os.path.exists(os.path.join(data_dir, "pending_render.json"))


def _point_filemanager_at(monkeypatch, data_dir):
    """Make FileManager().base_dir == data_dir, matching the real dev daemon where
    the task config and the pending-render manifest live in the same directory."""
    class _FM:
        base_dir = data_dir
    monkeypatch.setattr("file_manager.FileManager", lambda: _FM())


def test_has_pending_render(tmp_path, monkeypatch):
    _point_filemanager_at(monkeypatch, str(tmp_path))
    s = _bare_scheduler()
    s.data_dir = str(tmp_path)

    class _Pipeline:
        task_type = "briefing_pipeline"

    class _Extract:
        task_type = "extraction"

    # No manifest yet.
    assert s._has_pending_render(_Pipeline()) is False
    # Manifest for today → pending.
    with open(os.path.join(str(tmp_path), "pending_render.json"), "w") as f:
        json.dump({"date": dt.date.today().isoformat()}, f)
    assert s._has_pending_render(_Pipeline()) is True
    # Non-pipeline task never counts.
    assert s._has_pending_render(_Extract()) is False
    # Stale (previous day) manifest → not pending today.
    with open(os.path.join(str(tmp_path), "pending_render.json"), "w") as f:
        json.dump({"date": "2020-01-01"}, f)
    assert s._has_pending_render(_Pipeline()) is False


def _seed_pipeline_task(data_dir, next_run):
    task = {
        "id": "t1", "name": "News Pipeline", "enabled": True,
        "task_type": "briefing_pipeline", "interval": "daily", "run_at_time": "07:00",
        "last_run": dt.datetime.now().isoformat(),  # already ran today
        "next_run": next_run,
    }
    with open(os.path.join(data_dir, "scheduled_tasks.json"), "w") as f:
        json.dump({"tasks": [task]}, f)


def test_load_tasks_preserves_pending_render_retry(tmp_path, monkeypatch):
    """The critical race: load_tasks() runs every 60s and normally resets next_run to
    the daily schedule. With a pending render it MUST keep the short retry."""
    data_dir = str(tmp_path)
    _point_filemanager_at(monkeypatch, data_dir)
    retry = (dt.datetime.now() + dt.timedelta(minutes=15)).isoformat()
    _seed_pipeline_task(data_dir, retry)
    with open(os.path.join(data_dir, "pending_render.json"), "w") as f:
        json.dump({"date": dt.date.today().isoformat(), "video_ids": ["v1"], "note_paths": []}, f)

    s = scheduler_mod.Scheduler(data_dir=data_dir)  # __init__ calls load_tasks()
    nr = dt.datetime.fromisoformat(s.tasks[0].next_run)
    assert dt.datetime.now() < nr <= dt.datetime.now() + dt.timedelta(hours=1)


def test_load_tasks_resets_next_run_without_pending_render(tmp_path, monkeypatch):
    """No pending render → load_tasks resets to the daily schedule (not the retry)."""
    data_dir = str(tmp_path)
    _point_filemanager_at(monkeypatch, data_dir)  # isolate from any real repo manifest
    retry = (dt.datetime.now() + dt.timedelta(minutes=15)).isoformat()
    _seed_pipeline_task(data_dir, retry)  # no manifest written

    s = scheduler_mod.Scheduler(data_dir=data_dir)
    assert s.tasks[0].next_run != retry  # recomputed to daily, not the 15-min retry


def test_pipeline_gate_defers_and_writes_manifest(tmp_path, monkeypatch):
    """Integration: drive the REAL gate block inside _execute_pipeline_task via the
    resume path (summary exists, audio missing → no network fetch). When the gate
    reports blocked, the task must return the defer sentinel, set a short retry
    next_run, and write a pending-render manifest — without generating audio."""
    import datetime as _dt
    data_dir = str(tmp_path)

    # FileManager: base_dir=data_dir, provide an API key so the pre-flight passes.
    class _FM:
        base_dir = data_dir
        def load_api_key(self):
            return "test-key"
    monkeypatch.setattr("file_manager.FileManager", lambda: _FM())

    # One enabled source so the "no enabled sources" guard passes (load_sources is
    # called before the checkpoint even on the resume path).
    class _Src:
        enabled = True
        name = "s"
    monkeypatch.setattr("source_fetcher.load_sources", lambda *a, **k: [_Src()])

    # Force the gate to report the machine busy.
    monkeypatch.setattr("briefing_gate.render_blocked", lambda *a, **k: (True, "app running: openmw"))
    # Pin the cutoff above any wall-clock hour: with the default giveup_hour=22 this
    # test gives up (returns None) instead of deferring when CI runs late in the
    # UTC day — it failed at 22:56Z on 2026-09-03.
    with open(os.path.join(data_dir, "briefing_gate.json"), "w") as f:
        json.dump({"giveup_hour": 25, "retry_interval_min": 15}, f)

    # Today's summary text exists but no audio → partial checkpoint → resume at TTS.
    today = _dt.date.today()
    year, week, _ = today.isocalendar()
    wk = tmp_path / f"Week_{week}_{year}"
    wk.mkdir()
    (wk / f"{today.isoformat()}_News.txt").write_text("Some briefing text.\n")

    from scheduler import ScheduledTask
    task = ScheduledTask(id="t1", name="News Pipeline", task_type="briefing_pipeline",
                         audio_quality="quality", upload_to_drive=False)

    s = _bare_scheduler()
    result = s._execute_pipeline_task(task)

    assert result == "__DEFER__"
    nr = _dt.datetime.fromisoformat(task.next_run)
    assert _dt.datetime.now() < nr <= _dt.datetime.now() + _dt.timedelta(hours=1)
    # No audio was generated.
    assert not (wk / f"{today.isoformat()}_News.mp3").exists()
    # Manifest written for today.
    manifest = json.load(open(os.path.join(data_dir, "pending_render.json")))
    assert manifest["date"] == today.isoformat()


def _drive_ok(monkeypatch):
    monkeypatch.setattr("drive_manager.is_reauth_needed", lambda: False)
    monkeypatch.setattr("drive_manager.is_signed_in", lambda: True)


def _pipeline_task(**over):
    from scheduler import ScheduledTask
    kw = dict(id="t1", name="News Pipeline", task_type="briefing_pipeline",
              upload_to_drive=True, drive_folder_id="folder123")
    kw.update(over)
    return ScheduledTask(**kw)


def test_upload_retry_worthwhile(monkeypatch):
    _drive_ok(monkeypatch)
    s = _bare_scheduler()
    assert s._upload_retry_is_worthwhile(_pipeline_task()) is True
    assert s._upload_retry_is_worthwhile(_pipeline_task(upload_to_drive=False)) is False
    assert s._upload_retry_is_worthwhile(_pipeline_task(drive_folder_id="")) is False


def test_upload_retry_not_worthwhile_on_reauth(monkeypatch):
    monkeypatch.setattr("drive_manager.is_reauth_needed", lambda: True)
    monkeypatch.setattr("drive_manager.is_signed_in", lambda: True)
    s = _bare_scheduler()
    assert s._upload_retry_is_worthwhile(_pipeline_task()) is False


def test_upload_retry_not_worthwhile_when_signed_out(monkeypatch):
    monkeypatch.setattr("drive_manager.is_reauth_needed", lambda: False)
    monkeypatch.setattr("drive_manager.is_signed_in", lambda: False)
    s = _bare_scheduler()
    assert s._upload_retry_is_worthwhile(_pipeline_task()) is False


def test_maybe_defer_upload_retry_before_cutoff(tmp_path, monkeypatch):
    _drive_ok(monkeypatch)
    data_dir = str(tmp_path)
    # giveup_hour=25 → current hour is always < cutoff → retry.
    with open(os.path.join(data_dir, "briefing_gate.json"), "w") as f:
        json.dump({"giveup_hour": 25, "retry_interval_min": 15}, f)
    s = _bare_scheduler()
    t = _pipeline_task(last_result="OK: audio generated, Drive upload failed")
    r = s._maybe_defer_upload_retry(t, data_dir, dt.date.today(), _FakeFetcher(["v1"]), [])
    assert r == "__DEFER__"
    nr = dt.datetime.fromisoformat(t.next_run)
    assert dt.datetime.now() < nr <= dt.datetime.now() + dt.timedelta(hours=1)
    # Manifest carries the fetcher's IDs for the eventual successful upload.
    m = json.load(open(os.path.join(data_dir, "pending_render.json")))
    assert m["video_ids"] == ["v1"]


def test_maybe_defer_upload_retry_gives_up_past_cutoff(tmp_path, monkeypatch):
    _drive_ok(monkeypatch)
    data_dir = str(tmp_path)
    # giveup_hour=0 → current hour is always >= cutoff → give up.
    with open(os.path.join(data_dir, "briefing_gate.json"), "w") as f:
        json.dump({"giveup_hour": 0}, f)
    with open(os.path.join(data_dir, "pending_render.json"), "w") as f:
        json.dump({"date": dt.date.today().isoformat(), "video_ids": ["x"], "note_paths": []}, f)
    s = _bare_scheduler()
    r = s._maybe_defer_upload_retry(_pipeline_task(), data_dir, dt.date.today(), None, [])
    assert r is None  # falls through to the daily schedule
    assert not os.path.exists(os.path.join(data_dir, "pending_render.json"))  # discarded


def test_maybe_defer_upload_retry_none_when_not_configured(tmp_path, monkeypatch):
    s = _bare_scheduler()
    r = s._maybe_defer_upload_retry(_pipeline_task(upload_to_drive=False),
                                    str(tmp_path), dt.date.today(), None, [])
    assert r is None


def test_resume_defer_preserves_manifest(tmp_path):
    """A fresh defer writes the manifest; a resume-defer (fetcher=None) must not
    overwrite it with empties — the pipeline only calls write when fetcher is not
    None, so simulate that contract here."""
    s = _bare_scheduler()
    data_dir = str(tmp_path)
    today = dt.date(2026, 7, 12)
    # Fresh defer.
    s._pipeline_write_render_manifest(data_dir, today, _FakeFetcher(["v1", "v2"]), [])
    # Resume-defer would NOT call write (fetcher is None). Manifest stays intact.
    m = json.load(open(os.path.join(data_dir, "pending_render.json")))
    assert m["video_ids"] == ["v1", "v2"]
