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


class _Resp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


GOOD_HTML = """<html><head><title>Good Page</title></head><body>
<nav><p>navigation text that is long enough to be a paragraph but is in nav</p></nav>
<article>
<p>This is the first real paragraph of the article and it is longer than fifty characters.</p>
<p>short</p>
<p>This is the second real paragraph of the article and it is also longer than fifty chars.</p>
</article></body></html>"""

SHORT_HTML = "<html><head><title>Tiny</title></head><body><article><p>Too short.</p></article></body></html>"


def test_strip_utm():
    assert audio_jobs.strip_utm("https://a.b/c?utm_source=x&id=1&utm_medium=y") == "https://a.b/c?id=1"
    assert audio_jobs.strip_utm("https://a.b/c?utm_source=x") == "https://a.b/c"


def test_fetch_articles_good_page(monkeypatch):
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(GOOD_HTML))
    seen = []
    arts = audio_jobs.fetch_articles(["https://x.y/p?utm_source=z"], progress=seen.append)
    assert len(arts) == 1
    a = arts[0]
    assert a["url"] == "https://x.y/p"
    assert a["title"] == "Good Page"
    assert a["error"] is None
    assert "first real paragraph" in a["content"]
    assert "navigation text" not in a["content"]
    assert "short" not in a["content"].split("\n\n")
    assert seen and "1/1" in seen[0]


def test_fetch_articles_too_short_is_recorded_not_dropped(monkeypatch):
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(SHORT_HTML))
    arts = audio_jobs.fetch_articles(["https://x.y/short"])
    assert arts[0]["content"] == ""
    assert "too short" in arts[0]["error"]


def test_fetch_articles_http_error_is_recorded(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("timeout")
    monkeypatch.setattr(audio_jobs.requests, "get", boom)
    arts = audio_jobs.fetch_articles(["https://x.y/err"])
    assert arts[0]["content"] == ""
    assert "timeout" in arts[0]["error"]


def test_fetch_articles_cancel_raises(monkeypatch):
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(GOOD_HTML))
    import pytest
    with pytest.raises(audio_jobs.CancelledError):
        audio_jobs.fetch_articles(["https://x.y/1", "https://x.y/2"], cancel=lambda: True)
