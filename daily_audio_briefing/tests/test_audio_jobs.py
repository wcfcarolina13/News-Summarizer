"""Tests for audio_jobs — the Tk-free audio pipeline core."""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import audio_jobs  # noqa: E402
import file_manager  # noqa: E402

FIXED = datetime.datetime(2026, 9, 3, 10, 0, 0)


def test_data_directory_dev_mode_is_script_dir(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    expected = os.path.dirname(os.path.abspath(file_manager.__file__))
    assert file_manager.get_data_directory() == expected


def test_constants():
    assert audio_jobs.DEFAULT_VOICE == "af_sarah"
    assert audio_jobs.DEFAULT_VOICE in audio_jobs.KOKORO_VOICES
    assert len(audio_jobs.KOKORO_VOICES) == 12
    assert audio_jobs.READING_LIST_SUBDIR == "Reading List"
    assert audio_jobs.QUALITIES == ("quality", "fast")


def test_generate_audio_filename_uses_first_line_as_title():
    name = audio_jobs.generate_audio_filename(
        "Bitcoin ETF Approval Shakes Markets\n\nBody text here.", "wav", now=FIXED)
    assert name == "2026-09-03_bitcoin-etf-approval-shakes.wav"


def test_generate_audio_filename_short_text_falls_back():
    assert audio_jobs.generate_audio_filename("hi", "mp3", now=FIXED) == "2026-09-03_audio.mp3"


def test_reading_list_basename_joins_up_to_three_slugs():
    name = audio_jobs.reading_list_basename(
        ["First Article!", "Second: One", "Third", "Fourth"], now=FIXED)
    assert name == "2026-09-03_reading-list_first-article_second-one_third"


def test_reading_list_basename_empty_titles():
    assert audio_jobs.reading_list_basename([], now=FIXED) == "2026-09-03_reading-list_reading-list"
