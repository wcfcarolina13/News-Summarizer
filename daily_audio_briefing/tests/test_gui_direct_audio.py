"""Headless tests for the Direct Audio cleaning path (`clean_text_for_listening`).

Exercised unbound against a lightweight stub `self`, so no Tk window is created.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

gui_app = pytest.importorskip("gui_app", reason="gui_app requires a display / GUI deps")
import audio_jobs  # noqa: E402


class _Stub:
    def __init__(self, model_label="Fast (FREE)"):
        self.model_var = types.SimpleNamespace(get=lambda: model_label)

    def _get_active_article_instructions(self):
        return "INSTR"


def _patch_clean(monkeypatch, calls):
    def fake_clean(text, *, api_key, instructions="", model_name=None, progress=None):
        calls.append({"text": text, "api_key": api_key,
                      "instructions": instructions, "model_name": model_name})
        return "CLEAN:" + text.strip()
    monkeypatch.setattr(gui_app.audio_jobs, "clean_text", fake_clean)


def test_single_article_delegates_to_audio_jobs(monkeypatch):
    calls = []
    _patch_clean(monkeypatch, calls)
    out = gui_app.AudioBriefingApp.clean_text_for_listening(_Stub(), "hello", "KEY")
    assert out == "CLEAN:hello"
    assert len(calls) == 1
    assert calls[0]["api_key"] == "KEY"
    assert calls[0]["instructions"] == "INSTR"
    assert calls[0]["model_name"] == "gemini-2.0-flash"


def test_multi_article_split_cleans_each(monkeypatch):
    calls = []
    _patch_clean(monkeypatch, calls)
    a = "A" * 150
    b = "B" * 150
    out = gui_app.AudioBriefingApp.clean_text_for_listening(
        _Stub(), a + "\n\n---\n\n" + b, "KEY")
    assert len(calls) == 2
    assert out == "CLEAN:" + a + "\n\nCLEAN:" + b


def test_short_articles_skipped(monkeypatch):
    calls = []
    _patch_clean(monkeypatch, calls)
    long = "L" * 150
    gui_app.AudioBriefingApp.clean_text_for_listening(
        _Stub(), "tiny\n\n---\n\n" + long, "KEY")
    assert len(calls) == 1


def test_unknown_model_label_falls_back_to_default(monkeypatch):
    calls = []
    _patch_clean(monkeypatch, calls)
    gui_app.AudioBriefingApp.clean_text_for_listening(_Stub("???"), "hello", "KEY")
    assert calls[0]["model_name"] == audio_jobs.DEFAULT_CLEAN_MODEL


def test_filename_helper_is_the_core_one():
    assert not hasattr(gui_app.AudioBriefingApp, "generate_audio_filename")
    assert not hasattr(gui_app.AudioBriefingApp, "_clean_single_article")
    name = gui_app.audio_jobs.generate_audio_filename("Bitcoin ETF approval news", "wav")
    assert name.endswith(".wav")
