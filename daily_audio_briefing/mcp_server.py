"""
mcp_server — stdio MCP server exposing the Daily Audio Briefing audio pipeline.

Tools: text_to_audio, urls_to_audio, get_job, list_jobs, list_voices.
Jobs run on ONE worker thread (Kokoro should not run twice at once) and are
recorded by job_store.JobStore under <data_dir>/jobs/.

Never print to stdout here: stdout is the MCP transport.
"""
import argparse
import logging
import os
import queue
import sys
import threading
from typing import Optional

from mcp.server.fastmcp import FastMCP

import audio_jobs
import llm_fallback
from file_manager import get_data_directory
from job_store import JobStore

SERVER_NAME = "daily-audio-briefing"
MAX_URLS = 50
MAX_TEXT_CHARS = 400_000

log = logging.getLogger("dab.mcp")

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _configure_logging(data_dir: str) -> None:
    """Attach a file handler to the 'dab.mcp' logger.

    basicConfig is a no-op once the root logger has handlers (pytest, or any
    earlier import), so the handler is added explicitly here. Idempotent: the
    same log path is never attached twice.
    """
    path = os.path.join(data_dir, "mcp_server.log")
    logging.basicConfig(filename=path, level=logging.INFO, format=_LOG_FORMAT)
    for h in log.handlers:
        if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == os.path.abspath(path):
            return
    try:
        handler = logging.FileHandler(path)
    except OSError:  # unwritable data dir must not kill the server
        return
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class _Worker:
    """FIFO single-thread job runner."""

    def __init__(self, store: JobStore, data_dir: str):
        self.store = store
        self.data_dir = data_dir
        self.q: "queue.Queue[tuple[str, dict]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._loop, name="dab-mcp-worker", daemon=True)
                self._thread.start()

    def submit(self, job_id, params):
        self.start()
        self.q.put((job_id, params))

    def _loop(self):
        while True:
            job_id, params = self.q.get()
            try:
                self._run(job_id, params)
            except Exception as e:  # noqa: BLE001 — last-resort guard so the worker never dies
                log.exception("job %s crashed", job_id)
                try:
                    self.store.update(job_id, state="failed", error=str(e))
                except Exception:
                    pass
            finally:
                self.q.task_done()

    def _run(self, job_id, params):
        self.store.update(job_id, state="running", progress="starting")
        progress = lambda msg: self.store.update(job_id, progress=msg)  # noqa: E731
        out_dir = os.path.join(self.data_dir, audio_jobs.READING_LIST_SUBDIR)
        try:
            api_key = audio_jobs.load_gemini_api_key(self.data_dir)
            instructions = audio_jobs.load_article_instructions(self.data_dir)
            if params["kind"] == "text_to_audio":
                out = audio_jobs.text_to_audio(
                    params["text"], title=params.get("title"), voice=params["voice"],
                    quality=params["quality"], output_dir=out_dir, progress=progress)
                text_path = os.path.splitext(out)[0] + ".txt"
                update_kwargs = {"state": "done", "output_path": out, "progress": "done"}
            else:
                res = audio_jobs.urls_to_audio(
                    params["urls"], title=params.get("title"), voice=params["voice"],
                    quality=params["quality"], api_key=api_key, instructions=instructions,
                    output_dir=out_dir, progress=progress)
                slim = [{"url": a["url"], "title": a["title"], "error": a["error"]}
                        for a in res["articles"]]
                out = res["output_path"]
                text_path = res["text_path"]
                update_kwargs = {"state": "done", "output_path": out, "progress": "done",
                                 "articles": slim, "skipped": res["skipped"]}

            if params.get("upload_to_drive"):
                drive_result = audio_jobs.upload_outputs_to_drive(
                    [out, text_path], params.get("drive_folder"),
                    data_dir=self.data_dir, progress=progress)
                update_kwargs["drive"] = drive_result
                if drive_result.get("status") == "error":
                    update_kwargs["progress"] = f"done (Drive upload failed: {drive_result.get('error')})"

            self.store.update(job_id, **update_kwargs)
        except Exception as e:  # noqa: BLE001 — every pipeline failure becomes a failed job
            log.warning("job %s failed: %s", job_id, e)
            self.store.update(job_id, state="failed", error=str(e))


def _validate_common(voice, quality):
    if voice not in audio_jobs.KOKORO_VOICES:
        raise ValueError(f"unknown voice {voice!r}; see list_voices")
    if quality not in audio_jobs.QUALITIES:
        raise ValueError(f"quality must be one of {audio_jobs.QUALITIES}")


def build_server(data_dir: Optional[str] = None) -> FastMCP:
    # stdout is the MCP transport — silence the LLM fallback chain's prints
    # before anything can run on the worker thread.
    os.environ.setdefault("DEBUG_FALLBACK", "0")
    llm_fallback.LOG_TO_STDOUT = False

    data_dir = data_dir or get_data_directory()
    os.makedirs(data_dir, exist_ok=True)
    _configure_logging(data_dir)
    store = JobStore(os.path.join(data_dir, "jobs"))
    recovered = store.recover_interrupted()
    if recovered:
        log.info("marked %d interrupted job(s) failed", recovered)
    worker = _Worker(store, data_dir)
    mcp = FastMCP(SERVER_NAME, instructions=(
        "Turn text or article URLs into audio using the Daily Audio Briefing app. "
        "text_to_audio / urls_to_audio start a background job and return a job_id; "
        "poll get_job until state is done or failed. Output files land in the app's "
        "'Reading List' folder. Set upload_to_drive=true to also push the MP3 and TXT "
        "to the app's Drive folder, the one the daily briefing uses; drive_folder overrides it."))

    def _validate_drive_folder(drive_folder):
        if drive_folder is not None and not drive_folder.strip():
            raise ValueError("drive_folder is empty; omit it to use the configured folder")

    @mcp.tool()
    def text_to_audio(text: str, title: Optional[str] = None,
                      voice: str = audio_jobs.DEFAULT_VOICE, quality: str = "quality",
                      upload_to_drive: bool = False, drive_folder: Optional[str] = None) -> dict:
        """Start a job that converts TEXT to speech. quality: 'quality' (Kokoro) or 'fast' (gTTS).

        Set upload_to_drive=true to also push the MP3 and TXT to the app's Drive folder,
        the one the daily briefing uses; drive_folder overrides it.
        """
        if not text or not text.strip():
            raise ValueError("text is empty")
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"text is {len(text)} chars; limit is {MAX_TEXT_CHARS}")
        _validate_common(voice, quality)
        _validate_drive_folder(drive_folder)
        job = store.create("text_to_audio", {"title": title, "voice": voice, "quality": quality,
                                             "chars": len(text)}, None)
        worker.submit(job["job_id"], {"kind": "text_to_audio", "text": text, "title": title,
                                      "voice": voice, "quality": quality,
                                      "upload_to_drive": upload_to_drive, "drive_folder": drive_folder})
        return {"job_id": job["job_id"], "state": "queued",
                "output_dir": os.path.join(data_dir, audio_jobs.READING_LIST_SUBDIR)}

    @mcp.tool()
    def urls_to_audio(urls: list[str], title: Optional[str] = None,
                      voice: str = audio_jobs.DEFAULT_VOICE, quality: str = "quality",
                      upload_to_drive: bool = False, drive_folder: Optional[str] = None) -> dict:
        """Start a job that fetches each URL, cleans the article text, and reads them in order.

        Set upload_to_drive=true to also push the MP3 and TXT to the app's Drive folder,
        the one the daily briefing uses; drive_folder overrides it.
        """
        if not urls:
            raise ValueError("urls is empty")
        if len(urls) > MAX_URLS:
            raise ValueError(f"{len(urls)} urls; limit is {MAX_URLS}")
        bad = [u for u in urls if not u.lower().startswith(("http://", "https://"))]
        if bad:
            raise ValueError(f"not http(s) URLs: {bad[:3]}")
        for u in urls:
            if not audio_jobs.is_public_http_url(u):
                raise ValueError(
                    f"refusing non-public or unresolvable URL: {u} "
                    f"(set {audio_jobs.ALLOW_PRIVATE_ENV}=1 to allow private hosts)")
        _validate_common(voice, quality)
        _validate_drive_folder(drive_folder)
        job = store.create("urls_to_audio", {"title": title, "voice": voice, "quality": quality,
                                             "urls": urls}, None)
        worker.submit(job["job_id"], {"kind": "urls_to_audio", "urls": urls, "title": title,
                                      "voice": voice, "quality": quality,
                                      "upload_to_drive": upload_to_drive, "drive_folder": drive_folder})
        return {"job_id": job["job_id"], "state": "queued",
                "output_dir": os.path.join(data_dir, audio_jobs.READING_LIST_SUBDIR)}

    @mcp.tool()
    def get_job(job_id: str) -> dict:
        """Status of one job: state (queued|running|done|failed), progress, output_path, error."""
        job = store.get(job_id)
        if job is None:
            raise ValueError(f"unknown job_id {job_id!r}")
        return job

    @mcp.tool()
    def list_jobs(limit: int = 20) -> dict:
        """Most recent jobs, newest first."""
        return {"jobs": store.list(limit=max(1, min(int(limit), 200)))}

    @mcp.tool()
    def list_voices() -> dict:
        """Kokoro voice ids accepted by the voice argument."""
        return {"voices": list(audio_jobs.KOKORO_VOICES), "default": audio_jobs.DEFAULT_VOICE}

    return mcp


def main(argv=None):
    import json
    import mcp_config

    parser = argparse.ArgumentParser(prog="dab-mcp", description="Daily Audio Briefing MCP server (stdio)")
    parser.add_argument("--data-dir", default=None, help="override the data directory")
    parser.add_argument("--print-config", action="store_true", help="print the MCP client config snippet")
    parser.add_argument("--install", action="store_true", help="add this server to Claude Code + Claude Desktop configs")
    parser.add_argument("--uninstall", action="store_true", help="remove this server from those configs")
    parser.add_argument("--check", action="store_true", help="build the server, list tools, exit 0")
    args = parser.parse_args(argv)

    if args.print_config:
        print(json.dumps(mcp_config.snippet(mcp_config.server_command()), indent=2))
        return 0
    if args.install:
        try:
            for p in mcp_config.install(mcp_config.server_command()):
                print(f"installed {mcp_config.SERVER_KEY} -> {p}")
        except mcp_config.ConfigError as e:
            print(str(e), file=sys.stderr)
            return 1
        print("Restart Claude Code / Claude Desktop to pick it up.")
        return 0
    if args.uninstall:
        try:
            for p in mcp_config.uninstall():
                print(f"removed {mcp_config.SERVER_KEY} from {p}")
        except mcp_config.ConfigError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0
    if args.check:
        server = build_server(args.data_dir)
        import asyncio
        names = [t.name for t in asyncio.run(server.list_tools())]
        print("ok:", ", ".join(names))
        return 0
    build_server(args.data_dir).run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
