"""Regression tests for the scrapetube hang that froze the daemon (2026-08).

Bug: `fetch_channel_videos_with_fallback` called
`list(scrapetube.get_channel(...))` with no timeout. scrapetube passes no
`timeout=` to its requests session, and no global socket timeout is set, so a
YouTube-side stall blocks in recv() forever. It never returns and never raises,
so the surrounding try/except and the healthy RSS fallback below it are both
unreachable. Because scheduler._run_loop executes tasks inline, that single
blocked read froze the entire daemon for ~33h (Aug 1 -> Aug 2), killing all
three scheduled tasks, with no notification (a hang reaches no callback).

Fix: bound the scrapetube attempt with a hard timeout, then fall through to RSS.
Plus a per-process circuit breaker so a broadly-broken scrapetube doesn't burn
the timeout once per channel on every run.
"""
import os
import sys
import threading
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import youtube_rss


def _fake_scrapetube(behavior):
    """Build a stand-in `scrapetube` module. `behavior` is called by get_channel."""
    mod = types.ModuleType("scrapetube")
    mod.calls = 0

    def get_channel(channel_url=None, limit=None, **kwargs):
        mod.calls += 1
        return behavior()

    mod.get_channel = get_channel
    return mod


def _hanging_gen(stop_event):
    def _gen():
        # Blocks on first next(), exactly like a stalled socket read inside
        # scrapetube's pagination generator.
        stop_event.wait(30)
        yield {"videoId": "never-arrives"}
    return _gen


def _rss_stub(*_args, **_kwargs):
    return [{"videoId": "rss-1"}, {"videoId": "rss-2"}]


def test_hanging_scrapetube_falls_back_to_rss_within_timeout(monkeypatch):
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    started = time.time()
    try:
        out = youtube_rss.fetch_channel_videos_with_fallback(
            "https://www.youtube.com/@Hangs/videos", limit=5, scrapetube_timeout=1.0
        )
        elapsed = time.time() - started
    finally:
        stop.set()  # let the orphaned worker thread exit

    # The whole point: a hang must not block the caller indefinitely.
    assert elapsed < 10, f"call took {elapsed:.1f}s — the timeout did not bound it"
    assert out == _rss_stub(), "RSS fallback should have supplied the videos"


def test_repeated_hangs_trip_circuit_breaker(monkeypatch):
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    try:
        for _ in range(4):
            youtube_rss.fetch_channel_videos_with_fallback(
                "https://www.youtube.com/@Hangs/videos", limit=5, scrapetube_timeout=0.5
            )
    finally:
        stop.set()

    # After the failure limit, scrapetube must not be attempted again this run —
    # otherwise 12 broken channels cost 12 x timeout of dead wall-clock daily.
    assert fake.calls == youtube_rss.SCRAPETUBE_FAILURE_LIMIT, (
        f"scrapetube called {fake.calls}x; circuit should have opened after "
        f"{youtube_rss.SCRAPETUBE_FAILURE_LIMIT}"
    )


def test_working_scrapetube_is_still_preferred(monkeypatch):
    videos = [{"videoId": f"st-{i}"} for i in range(3)]
    fake = _fake_scrapetube(lambda: iter(videos))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@Works/videos", limit=5, scrapetube_timeout=5.0
    )

    # No behaviour change when scrapetube is healthy.
    assert out == videos


def test_raising_scrapetube_still_falls_back(monkeypatch):
    def _boom():
        raise RuntimeError("IncompleteRead")

    fake = _fake_scrapetube(_boom)
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@Raises/videos", limit=5, scrapetube_timeout=5.0
    )

    assert out == _rss_stub()
