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


def test_build_clean_prompt_with_and_without_instructions():
    p = audio_jobs.build_clean_prompt("BODY", "")
    assert "TEXT TO CLEAN" in p and "BODY" in p and "ADDITIONAL USER PREFERENCES" not in p
    p2 = audio_jobs.build_clean_prompt("BODY", "drop sponsor reads")
    assert "5. ADDITIONAL USER PREFERENCES:\ndrop sponsor reads" in p2


def test_clean_text_no_key_returns_input(monkeypatch):
    seen = []
    out = audio_jobs.clean_text("raw text", api_key="", progress=seen.append)
    assert out == "raw text"
    assert any("skipping" in m.lower() for m in seen)


def test_clean_text_uses_fallback_chain(monkeypatch):
    calls = {}

    def fake_generate(prompt, gemini_model=None, caller="", timeout=120):
        calls["prompt"] = prompt
        calls["caller"] = caller
        return "  cleaned  "

    monkeypatch.setattr(audio_jobs, "_configure_gemini", lambda key, model_name: "MODEL")
    monkeypatch.setattr(audio_jobs, "generate_with_fallback", fake_generate)
    assert audio_jobs.clean_text("raw", api_key="k") == "cleaned"
    assert "raw" in calls["prompt"] and calls["caller"] == "audio_jobs.clean_text"


def test_clean_text_failure_returns_input(monkeypatch):
    monkeypatch.setattr(audio_jobs, "_configure_gemini", lambda key, model_name: "MODEL")

    def boom(prompt, gemini_model=None, caller="", timeout=120):
        raise RuntimeError("provider down")

    monkeypatch.setattr(audio_jobs, "generate_with_fallback", boom)
    seen = []
    assert audio_jobs.clean_text("raw", api_key="k", progress=seen.append) == "raw"
    assert any("provider down" in m for m in seen)


def test_combine_articles_separators():
    arts = [
        {"url": "u1", "title": "First Title", "content": "x", "cleaned": "Body one.", "error": None},
        {"url": "u2", "title": "Second", "content": "y", "cleaned": "Body two.", "error": None},
        {"url": "u3", "title": "Bad", "content": "", "cleaned": "", "error": "too short"},
    ]
    out = audio_jobs.combine_articles(arts)
    assert out.startswith("First Title.\n\nBody one.")
    assert "\n\nNext article.\n\nSecond.\n\nBody two." in out
    assert "Bad" not in out


def test_load_article_instructions_strips_comments(tmp_path):
    import json
    (tmp_path / "instruction_profiles.json").write_text(json.dumps({
        "active_profile": "P",
        "profiles": {"P": {"article_instructions": "# comment\nkeep this\n\n  \nand this"}}
    }))
    assert audio_jobs.load_article_instructions(str(tmp_path)) == "keep this\nand this"


def test_load_article_instructions_missing_file(tmp_path):
    assert audio_jobs.load_article_instructions(str(tmp_path)) == ""


def test_load_gemini_api_key_env_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert audio_jobs.load_gemini_api_key(str(tmp_path)) == "from-env"
    (tmp_path / ".env").write_text("GEMINI_API_KEY=from-file\n")
    assert audio_jobs.load_gemini_api_key(str(tmp_path)) == "from-file"


def _stub_tts(monkeypatch):
    """Replace run_tts with a stub that writes the --output file and records argv."""
    calls = []

    def fake_run_tts(script, args, *, cwd, log_path):
        calls.append((script, list(args)))
        out = args[args.index("--output") + 1]
        with open(out, "wb") as f:
            f.write(b"RIFF")
        return 0

    monkeypatch.setattr(audio_jobs, "run_tts", fake_run_tts)
    monkeypatch.setattr(audio_jobs, "check_ffmpeg", lambda: False)
    return calls


def test_text_to_audio_quality_writes_file(tmp_path, monkeypatch):
    calls = _stub_tts(monkeypatch)
    out = audio_jobs.text_to_audio("Hello World Title\n\nBody.", voice="af_nova",
                                   quality="quality", output_dir=str(tmp_path))
    assert os.path.exists(out) and out.endswith(".wav")
    script, args = calls[0]
    assert script == "make_audio_quality.py"
    assert args[args.index("--voice") + 1] == "af_nova"
    assert os.path.exists(args[args.index("--input") + 1])  # text saved beside audio


def test_text_to_audio_fast_uses_gtts_and_mp3(tmp_path, monkeypatch):
    calls = _stub_tts(monkeypatch)
    out = audio_jobs.text_to_audio("Some text here.", quality="fast", output_dir=str(tmp_path))
    assert out.endswith(".mp3") and calls[0][0] == "make_audio_fast.py"


def test_text_to_audio_title_overrides_filename(tmp_path, monkeypatch):
    _stub_tts(monkeypatch)
    out = audio_jobs.text_to_audio("body", title="My Piece", quality="quality", output_dir=str(tmp_path))
    assert os.path.basename(out).endswith("_my-piece.wav")


def test_text_to_audio_validation(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        audio_jobs.text_to_audio("x", voice="nope", output_dir=str(tmp_path))
    with pytest.raises(ValueError):
        audio_jobs.text_to_audio("x", quality="ultra", output_dir=str(tmp_path))
    with pytest.raises(ValueError):
        audio_jobs.text_to_audio("   ", output_dir=str(tmp_path))


def test_text_to_audio_tts_failure_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_jobs, "run_tts", lambda *a, **k: 1)
    monkeypatch.setattr(audio_jobs, "check_ffmpeg", lambda: False)
    import pytest
    with pytest.raises(RuntimeError):
        audio_jobs.text_to_audio("body text", output_dir=str(tmp_path))


def test_urls_to_audio_end_to_end(tmp_path, monkeypatch):
    calls = _stub_tts(monkeypatch)
    pages = {"https://x.y/1": GOOD_HTML, "https://x.y/2": SHORT_HTML}
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(pages[url]))
    seen = []
    res = audio_jobs.urls_to_audio(list(pages), api_key="", output_dir=str(tmp_path), progress=seen.append)
    assert os.path.exists(res["output_path"])
    assert res["skipped"] == 1 and len(res["articles"]) == 2
    text = open(res["text_path"], encoding="utf-8").read()
    assert text.startswith("Good Page.")
    assert os.path.basename(res["output_path"]).startswith("2026-") or "_reading-list_" in res["output_path"]
    assert calls


def test_urls_to_audio_nothing_fetched_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(SHORT_HTML))
    import pytest
    with pytest.raises(RuntimeError, match="No article content"):
        audio_jobs.urls_to_audio(["https://x.y/short"], api_key="", output_dir=str(tmp_path))
