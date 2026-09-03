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
    class _Calls(list):
        """List of (script, args); also records the cwd each call ran with."""

    calls = _Calls()
    calls.cwds = []

    def fake_run_tts(script, args, *, cwd, log_path):
        calls.append((script, list(args)))
        calls.cwds.append(cwd)
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
    # frozen-mode chdir target: the data dir, not the output dir (Kokoro model lookup)
    assert calls.cwds[0] == file_manager.get_data_directory()


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


def test_urls_to_audio_passes_model_name(tmp_path, monkeypatch):
    _stub_tts(monkeypatch)
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(GOOD_HTML))
    seen = {}

    def fake_clean(text, *, api_key, instructions="", model_name="?", progress=None):
        seen["model"] = model_name
        return text

    monkeypatch.setattr(audio_jobs, "clean_text", fake_clean)
    audio_jobs.urls_to_audio(["https://x.y/1"], api_key="k", output_dir=str(tmp_path),
                             model_name="gemini-2.0-flash")
    assert seen["model"] == "gemini-2.0-flash"


# ---------------------------------------------------------------------------
# SSRF guard (used by the MCP server, which takes URLs from an agent).
# ---------------------------------------------------------------------------
def _fake_resolver(ip):
    return lambda host, port, *a, **kw: [(2, 1, 6, "", (ip, 0))]


def test_is_public_http_url_rejects_loopback(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("127.0.0.1"))
    assert audio_jobs.is_public_http_url("http://evil.test/x") is False


def test_is_public_http_url_rejects_private(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("10.0.0.1"))
    assert audio_jobs.is_public_http_url("https://evil.test/x") is False


def test_is_public_http_url_rejects_link_local_metadata(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("169.254.169.254"))
    assert audio_jobs.is_public_http_url("http://metadata.test/latest") is False


def test_is_public_http_url_allows_public(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("8.8.8.8"))
    assert audio_jobs.is_public_http_url("https://good.test/x") is True


def test_is_public_http_url_rejects_localhost_literal(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("8.8.8.8"))
    assert audio_jobs.is_public_http_url("http://localhost:8080/x") is False
    assert audio_jobs.is_public_http_url("http://127.0.0.1/x") is False


def test_is_public_http_url_rejects_non_http(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("8.8.8.8"))
    assert audio_jobs.is_public_http_url("file:///etc/passwd") is False


def test_is_public_http_url_env_override(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("127.0.0.1"))
    monkeypatch.setenv(audio_jobs.ALLOW_PRIVATE_ENV, "1")
    assert audio_jobs.is_public_http_url("http://127.0.0.1:5000/x") is True


class _RedirResp:
    def __init__(self, location, status=302):
        self.text = ""
        self.status_code = status
        self.headers = {"Location": location}

    def raise_for_status(self):
        pass


def test_fetch_articles_blocks_redirect_to_private_address(monkeypatch):
    monkeypatch.setattr(audio_jobs.socket, "getaddrinfo", _fake_resolver("8.8.8.8"))
    monkeypatch.setattr(audio_jobs.requests, "get",
                        lambda url, **kw: _RedirResp("http://169.254.169.254/latest/meta-data/"))
    arts = audio_jobs.fetch_articles(["https://good.test/p"])
    assert arts[0]["content"] == ""
    assert "non-public" in arts[0]["error"]


# ---------------------------------------------------------------------------
# Drive upload of MCP renders (load_drive_folder_id / upload_outputs_to_drive)
# ---------------------------------------------------------------------------
import sys as _sys
import types as _types


def _write_settings(tmp_path, **kv):
    import json as _json
    with open(os.path.join(str(tmp_path), "settings.json"), "w", encoding="utf-8") as f:
        _json.dump(kv, f)


def test_load_drive_folder_id_present(tmp_path):
    _write_settings(tmp_path, drive_folder_id="abc123")
    assert audio_jobs.load_drive_folder_id(str(tmp_path)) == "abc123"


def test_load_drive_folder_id_missing_file(tmp_path):
    assert audio_jobs.load_drive_folder_id(str(tmp_path)) == ""


def test_load_drive_folder_id_missing_key(tmp_path):
    _write_settings(tmp_path, other="x")
    assert audio_jobs.load_drive_folder_id(str(tmp_path)) == ""


def test_load_drive_folder_id_bad_json(tmp_path):
    with open(os.path.join(str(tmp_path), "settings.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    assert audio_jobs.load_drive_folder_id(str(tmp_path)) == ""


def _fake_drive_module(upload_results, *, signed_in=True, reauth_needed=False, raise_exc=None):
    calls = []

    def upload_file(local_path, folder_id, skip_existing=True):
        if raise_exc:
            raise raise_exc
        calls.append((local_path, folder_id))
        return upload_results[os.path.basename(local_path)]

    return _types.SimpleNamespace(
        upload_file=upload_file,
        is_signed_in=lambda: signed_in,
        is_reauth_needed=lambda: reauth_needed,
        extract_folder_id_from_url=lambda x: x,
    ), calls


def test_upload_outputs_to_drive_uploaded_and_skipped(tmp_path, monkeypatch):
    mp3 = os.path.join(str(tmp_path), "a.mp3")
    txt = os.path.join(str(tmp_path), "a.txt")
    open(mp3, "w").close()
    open(txt, "w").close()
    fake, calls = _fake_drive_module({
        "a.mp3": {"id": "1", "name": "a.mp3", "size_bytes": 10, "status": "uploaded"},
        "a.txt": {"id": "2", "name": "a.txt", "size_bytes": 5, "status": "skipped"},
    })
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    result = audio_jobs.upload_outputs_to_drive([mp3, txt], "folder123", data_dir=str(tmp_path))
    assert result["status"] == "uploaded"
    assert result["folder_id"] == "folder123"
    assert len(result["files"]) == 2
    assert {f["status"] for f in result["files"]} == {"uploaded", "skipped"}
    assert result["error"] is None
    assert len(calls) == 2


def test_upload_outputs_to_drive_one_error(tmp_path, monkeypatch):
    mp3 = os.path.join(str(tmp_path), "a.mp3")
    txt = os.path.join(str(tmp_path), "a.txt")
    open(mp3, "w").close()
    open(txt, "w").close()
    fake, _ = _fake_drive_module({
        "a.mp3": {"status": "uploaded", "id": "1", "name": "a.mp3", "size_bytes": 1},
        "a.txt": {"status": "error", "reason": "quota exceeded"},
    })
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    result = audio_jobs.upload_outputs_to_drive([mp3, txt], "folder123", data_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["error"] == "quota exceeded"


def test_upload_outputs_to_drive_reauth_needed(tmp_path, monkeypatch):
    fake, _ = _fake_drive_module({}, reauth_needed=True)
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    result = audio_jobs.upload_outputs_to_drive(["x.mp3"], "folder123", data_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["error"] == "Drive token expired — re-authenticate in Settings"


def test_upload_outputs_to_drive_not_signed_in(tmp_path, monkeypatch):
    fake, _ = _fake_drive_module({}, signed_in=False)
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    result = audio_jobs.upload_outputs_to_drive(["x.mp3"], "folder123", data_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["error"] == "Drive not signed in"


def test_upload_outputs_to_drive_no_folder_configured(tmp_path, monkeypatch):
    fake, _ = _fake_drive_module({})
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    result = audio_jobs.upload_outputs_to_drive(["x.mp3"], None, data_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["error"] == "no Drive folder configured"
    assert result["folder_id"] is None
    assert result["files"] == []


def test_upload_outputs_to_drive_uses_settings_folder_when_none_passed(tmp_path, monkeypatch):
    _write_settings(tmp_path, drive_folder_id="from-settings")
    mp3 = os.path.join(str(tmp_path), "a.mp3")
    open(mp3, "w").close()
    fake, calls = _fake_drive_module({"a.mp3": {"status": "uploaded", "id": "1", "name": "a.mp3", "size_bytes": 1}})
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    result = audio_jobs.upload_outputs_to_drive([mp3], "", data_dir=str(tmp_path))
    assert result["folder_id"] == "from-settings"
    assert result["status"] == "uploaded"


def test_upload_outputs_to_drive_raises_exception_caught(tmp_path, monkeypatch):
    fake, _ = _fake_drive_module({}, raise_exc=RuntimeError("boom"))
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    mp3 = os.path.join(str(tmp_path), "a.mp3")
    open(mp3, "w").close()
    result = audio_jobs.upload_outputs_to_drive([mp3], "folder123", data_dir=str(tmp_path))
    assert result["status"] == "error"
    assert result["error"] == "boom"


def test_upload_outputs_to_drive_reports_progress(tmp_path, monkeypatch):
    mp3 = os.path.join(str(tmp_path), "a.mp3")
    open(mp3, "w").close()
    fake, _ = _fake_drive_module({"a.mp3": {"status": "uploaded", "id": "1", "name": "a.mp3", "size_bytes": 1}})
    monkeypatch.setitem(_sys.modules, "drive_manager", fake)
    msgs = []
    audio_jobs.upload_outputs_to_drive([mp3], "folder123", data_dir=str(tmp_path), progress=msgs.append)
    assert any("Uploading to Drive" in m for m in msgs)
