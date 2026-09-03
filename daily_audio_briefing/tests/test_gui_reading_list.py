"""Headless tests for the Reading List dialog worker (`_process_reading_list_inner`).

The function is exercised unbound against a lightweight stub `self`, so no Tk
window is created.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

gui_app = pytest.importorskip("gui_app", reason="gui_app requires a display / GUI deps")
import audio_jobs  # noqa: E402


class _Stub:
    """Minimal stand-in for AudioBriefingApp."""

    def __init__(self):
        self.gemini_key_entry = types.SimpleNamespace(get=lambda: " key ")
        self.model_var = types.SimpleNamespace(get=lambda: "Fast (FREE)")
        self.voice_var = types.SimpleNamespace(get=lambda: "af_heart")
        self.reset_calls = []
        self.complete_calls = []

    def _get_active_article_instructions(self):
        return "INSTR"

    def _reset_reading_list_buttons(self, dialog, btn_process, btn_cancel):
        self.reset_calls.append(True)

    def _on_reading_list_complete(self, dialog, progress_label, btn_process,
                                  btn_cancel, success, basename, ext, size_mb,
                                  file_path=""):
        self.complete_calls.append((success, basename, ext, size_mb, file_path))


def _run(stub, cancelled=lambda: False, updates=None):
    updates = updates if updates is not None else []
    gui_app.AudioBriefingApp._process_reading_list_inner(
        stub, None, ["https://x.y/1"], None, None, None, None,
        cancelled, lambda msg, color="orange": updates.append((msg, color)))
    return updates


def test_success_path_delegates_and_reports(tmp_path, monkeypatch):
    stub = _Stub()
    audio = tmp_path / "2026-01-01_reading-list_x.mp3"
    audio.write_bytes(b"0" * 2048)
    seen = {}

    def fake(urls, **kw):
        seen.update(kw)
        seen["urls"] = urls
        return {"output_path": str(audio), "text_path": str(tmp_path / "x.txt"),
                "articles": [], "skipped": 0}

    monkeypatch.setattr(audio_jobs, "urls_to_audio", fake)
    _run(stub)

    assert seen["urls"] == ["https://x.y/1"]
    assert seen["api_key"] == "key"
    assert seen["instructions"] == "INSTR"
    assert seen["model_name"] == "gemini-2.0-flash"
    assert seen["voice"] == "af_heart"
    assert seen["quality"] == "quality"
    assert seen["output_dir"].endswith(audio_jobs.READING_LIST_SUBDIR)
    success, basename, ext, size_mb, file_path = stub.complete_calls[0]
    assert success is True
    assert basename == "2026-01-01_reading-list_x"
    assert ext == "mp3"
    assert file_path == str(audio)
    assert size_mb == pytest.approx(2048 / (1024 * 1024))


def test_cancel_resets_buttons(monkeypatch):
    stub = _Stub()

    def fake(urls, **kw):
        raise audio_jobs.CancelledError()

    monkeypatch.setattr(audio_jobs, "urls_to_audio", fake)
    updates = _run(stub)

    assert ("Cancelled.", "red") in updates
    assert stub.reset_calls == [True]
    assert stub.complete_calls == []


def test_no_content_reports_check_urls(monkeypatch):
    stub = _Stub()

    def fake(urls, **kw):
        raise RuntimeError("No article content could be fetched. Check URLs.")

    monkeypatch.setattr(audio_jobs, "urls_to_audio", fake)
    updates = _run(stub)

    assert ("No article content could be fetched. Check URLs.", "red") in updates
    assert stub.reset_calls == [True]
    assert stub.complete_calls == []


def test_tts_failure_reports_failure_completion(monkeypatch):
    stub = _Stub()

    def fake(urls, **kw):
        raise RuntimeError("TTS failed (exit 1)")

    monkeypatch.setattr(audio_jobs, "urls_to_audio", fake)
    _run(stub)

    assert stub.complete_calls == [(False, "", "", 0, "")]
