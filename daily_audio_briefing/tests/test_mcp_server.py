"""Drives the MCP server in-process through the SDK client with TTS stubbed."""
import asyncio
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import audio_jobs  # noqa: E402
import mcp_server  # noqa: E402
from mcp.shared.memory import create_connected_server_and_client_session as connect  # noqa: E402


@pytest.fixture
def stubbed(monkeypatch):
    def fake_run_tts(script, args, *, cwd, log_path):
        out = args[args.index("--output") + 1]
        open(out, "wb").write(b"RIFF")
        return 0
    monkeypatch.setattr(audio_jobs, "run_tts", fake_run_tts)
    monkeypatch.setattr(audio_jobs, "check_ffmpeg", lambda: False)
    monkeypatch.setattr(audio_jobs, "load_gemini_api_key", lambda data_dir=None: "")


def _call(server, name, args):
    async def go():
        async with connect(server._mcp_server) as client:
            res = await client.call_tool(name, args)
            return res
    return asyncio.run(go())


def _payload(res):
    """Structured content if present, else parse the first text block."""
    if getattr(res, "structuredContent", None):
        return res.structuredContent
    return json.loads(res.content[0].text)


def _wait_done(server, job_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = _payload(_call(server, "get_job", {"job_id": job_id}))
        if job["state"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_list_voices(tmp_path, stubbed):
    server = mcp_server.build_server(str(tmp_path))
    out = _payload(_call(server, "list_voices", {}))
    assert out["default"] == "af_sarah" and "bm_lewis" in out["voices"]


def test_text_to_audio_job_completes(tmp_path, stubbed):
    server = mcp_server.build_server(str(tmp_path))
    out = _payload(_call(server, "text_to_audio", {"text": "Hello there. This is a test.", "title": "Test Piece"}))
    assert out["state"] == "queued" and out["job_id"]
    job = _wait_done(server, out["job_id"])
    assert job["state"] == "done", job
    assert os.path.exists(job["output_path"])
    assert os.path.dirname(job["output_path"]) == os.path.join(str(tmp_path), "Reading List")


def test_urls_to_audio_job_completes(tmp_path, stubbed, monkeypatch):
    from tests.test_audio_jobs import GOOD_HTML, _Resp
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(GOOD_HTML))
    monkeypatch.setattr(audio_jobs, "is_public_http_url", lambda u: True)
    server = mcp_server.build_server(str(tmp_path))
    out = _payload(_call(server, "urls_to_audio", {"urls": ["https://x.y/1", "https://x.y/2"]}))
    job = _wait_done(server, out["job_id"])
    assert job["state"] == "done" and job["articles"][0]["title"] == "Good Page"
    listed = _payload(_call(server, "list_jobs", {}))
    assert listed["jobs"][0]["job_id"] == out["job_id"]


def test_validation_errors(tmp_path, stubbed):
    server = mcp_server.build_server(str(tmp_path))
    for name, args in [
        ("text_to_audio", {"text": "   "}),
        ("text_to_audio", {"text": "ok text", "voice": "nope"}),
        ("text_to_audio", {"text": "ok text", "quality": "ultra"}),
        ("text_to_audio", {"text": "x" * (mcp_server.MAX_TEXT_CHARS + 1)}),
        ("urls_to_audio", {"urls": []}),
        ("urls_to_audio", {"urls": ["ftp://nope"]}),
        ("urls_to_audio", {"urls": ["https://a.b"] * (mcp_server.MAX_URLS + 1)}),
    ]:
        res = _call(server, name, args)
        assert res.isError, (name, args)


def test_get_job_unknown(tmp_path, stubbed):
    server = mcp_server.build_server(str(tmp_path))
    assert _call(server, "get_job", {"job_id": "nope"}).isError


def test_tts_failure_marks_job_failed(tmp_path, stubbed, monkeypatch):
    monkeypatch.setattr(audio_jobs, "run_tts", lambda *a, **k: 1)
    server = mcp_server.build_server(str(tmp_path))
    out = _payload(_call(server, "text_to_audio", {"text": "will fail here"}))
    job = _wait_done(server, out["job_id"])
    assert job["state"] == "failed" and "TTS failed" in job["error"]


def test_urls_to_audio_rejects_loopback_url(tmp_path, stubbed):
    server = mcp_server.build_server(str(tmp_path))
    res = _call(server, "urls_to_audio", {"urls": ["http://127.0.0.1/x"]})
    assert res.isError


def test_job_articles_are_slim(tmp_path, stubbed, monkeypatch):
    from tests.test_audio_jobs import GOOD_HTML, _Resp
    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(GOOD_HTML))
    monkeypatch.setattr(audio_jobs, "is_public_http_url", lambda u: True)
    server = mcp_server.build_server(str(tmp_path))
    out = _payload(_call(server, "urls_to_audio", {"urls": ["https://x.y/1"]}))
    job = _wait_done(server, out["job_id"])
    assert job["state"] == "done", job
    art = job["articles"][0]
    assert set(art) == {"url", "title", "error"}
    assert "content" not in art and "cleaned" not in art


def test_worker_never_writes_to_stdout(tmp_path, stubbed, monkeypatch, capsys):
    """llm_fallback._log on the worker thread must not corrupt the stdio transport."""
    import io
    from contextlib import redirect_stdout
    import llm_fallback
    from tests.test_audio_jobs import GOOD_HTML, _Resp

    monkeypatch.setattr(audio_jobs.requests, "get", lambda url, **kw: _Resp(GOOD_HTML))
    monkeypatch.setattr(audio_jobs, "is_public_http_url", lambda u: True)
    monkeypatch.setattr(audio_jobs, "load_gemini_api_key", lambda data_dir=None: "k")
    monkeypatch.setattr(audio_jobs, "_configure_gemini", lambda *a, **kw: None)

    def fake_generate(*a, **kw):
        llm_fallback._log("provider x skipped")
        return "cleaned"

    monkeypatch.setattr(audio_jobs, "generate_with_fallback", fake_generate)

    buf = io.StringIO()
    with redirect_stdout(buf):
        server = mcp_server.build_server(str(tmp_path))
        out = _payload(_call(server, "urls_to_audio", {"urls": ["https://x.y/1"]}))
        job = _wait_done(server, out["job_id"])
    assert job["state"] == "done", job
    assert buf.getvalue() == ""
