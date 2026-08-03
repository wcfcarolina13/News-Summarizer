"""Regression tests for the scrapetube hang that froze the daemon (2026-08).

Bug: `fetch_channel_videos_with_fallback` called
`list(scrapetube.get_channel(...))` with no timeout. scrapetube passes no
`timeout=` to its requests session, and no global socket timeout is set, so a
YouTube-side stall blocks in recv() forever. It never returns and never raises,
so the surrounding try/except and the healthy RSS fallback below it are both
unreachable. Because scheduler._run_loop executes tasks inline, that single
blocked read froze the entire daemon for ~33h (Aug 1 -> Aug 2), killing all
three scheduled tasks, with no notification (a hang reaches no callback).

Fix, in two parts:
  1. Bound the scrapetube attempt with a hard timeout, plus a per-process
     circuit breaker so a broadly-broken scrapetube doesn't burn the timeout
     once per channel on every run.
  2. Prefer RSS (2026-08-03). scrapetube broke YouTube-side — it hangs on some
     channels and returns empty on others — while the RSS feed answers in <1s
     for every channel tested. scrapetube stays as the fallback (still
     timeout-bounded) for when RSS can't resolve a channel.
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


RSS_VIDEOS = [{"videoId": "rss-1"}, {"videoId": "rss-2"}]


def _rss_stub(*_args, **_kwargs):
    return list(RSS_VIDEOS)


def _rss_unavailable(*_args, **_kwargs):
    return None  # channel id unresolvable / feed fetch failed


def _rss_empty(*_args, **_kwargs):
    return []


# --- default ordering: RSS first --------------------------------------------

def test_rss_is_preferred_and_scrapetube_is_not_called(monkeypatch):
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    started = time.time()
    try:
        out = youtube_rss.fetch_channel_videos_with_fallback(
            "https://www.youtube.com/@Works/videos", limit=5
        )
        elapsed = time.time() - started
    finally:
        stop.set()

    assert out == RSS_VIDEOS
    # The whole point of RSS-first: a broken scrapetube costs nothing.
    assert fake.calls == 0, "scrapetube should not be touched when RSS answers"
    assert elapsed < 5


def test_scrapetube_used_when_rss_cannot_resolve(monkeypatch):
    videos = [{"videoId": "st-1"}]
    fake = _fake_scrapetube(lambda: iter(videos))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_unavailable)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@NoFeed/videos", limit=5, scrapetube_timeout=5.0,
        backends=("rss", "scrapetube"),
    )

    assert out == videos
    assert fake.calls == 1


def test_scrapetube_used_when_rss_returns_nothing(monkeypatch):
    videos = [{"videoId": "st-1"}]
    fake = _fake_scrapetube(lambda: iter(videos))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_empty)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@EmptyFeed/videos", limit=5, scrapetube_timeout=5.0,
        backends=("rss", "scrapetube"),
    )

    assert out == videos


def test_both_backends_failing_returns_empty_without_hanging(monkeypatch):
    # Worst case: RSS can't resolve AND scrapetube hangs. Must still return.
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_unavailable)
    youtube_rss.reset_scrapetube_circuit()

    started = time.time()
    try:
        out = youtube_rss.fetch_channel_videos_with_fallback(
            "https://www.youtube.com/@Doomed/videos", limit=5, scrapetube_timeout=1.0,
            backends=("rss", "scrapetube"),
        )
        elapsed = time.time() - started
    finally:
        stop.set()

    assert out == []
    assert elapsed < 10, f"call took {elapsed:.1f}s — the timeout did not bound it"


# --- three-backend chain: RSS -> yt-dlp -> scrapetube ------------------------

def test_default_order_is_rss_then_ytdlp_then_scrapetube():
    # yt-dlp sits ahead of scrapetube because scrapetube is the one that hangs.
    assert youtube_rss.DEFAULT_BACKENDS == ("rss", "ytdlp", "scrapetube")


def test_ytdlp_covers_for_a_failing_rss_without_touching_scrapetube(monkeypatch):
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_unavailable)
    ytdlp_videos = [{"videoId": "yt-1"}]
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_ytdlp",
                        lambda *a, **k: list(ytdlp_videos))
    youtube_rss.reset_scrapetube_circuit()

    try:
        out = youtube_rss.fetch_channel_videos_with_fallback(
            "https://www.youtube.com/@RssDown/videos", limit=5
        )
    finally:
        stop.set()

    assert out == ytdlp_videos
    assert fake.calls == 0, "scrapetube should never be reached when yt-dlp answers"


def test_scrapetube_is_last_resort_when_rss_and_ytdlp_both_fail(monkeypatch):
    videos = [{"videoId": "st-1"}]
    fake = _fake_scrapetube(lambda: iter(videos))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_unavailable)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_ytdlp", lambda *a, **k: None)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@AllDown/videos", limit=5, scrapetube_timeout=5.0
    )

    assert out == videos
    assert fake.calls == 1


# --- scrapetube path: still hang-proof in the fallback position --------------

def test_hanging_scrapetube_falls_back_to_rss_within_timeout(monkeypatch):
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    started = time.time()
    try:
        out = youtube_rss.fetch_channel_videos_with_fallback(
            "https://www.youtube.com/@Hangs/videos", limit=5,
            scrapetube_timeout=1.0, backends=("scrapetube", "rss"),
        )
        elapsed = time.time() - started
    finally:
        stop.set()  # let the orphaned worker thread exit

    assert elapsed < 10, f"call took {elapsed:.1f}s — the timeout did not bound it"
    assert out == RSS_VIDEOS, "RSS fallback should have supplied the videos"


def test_repeated_hangs_trip_circuit_breaker(monkeypatch):
    stop = threading.Event()
    fake = _fake_scrapetube(_hanging_gen(stop))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    try:
        for _ in range(4):
            youtube_rss.fetch_channel_videos_with_fallback(
                "https://www.youtube.com/@Hangs/videos", limit=5,
                scrapetube_timeout=0.5, backends=("scrapetube", "rss"),
            )
    finally:
        stop.set()

    # After the failure limit, scrapetube must not be attempted again this run.
    assert fake.calls == youtube_rss.SCRAPETUBE_FAILURE_LIMIT, (
        f"scrapetube called {fake.calls}x; circuit should have opened after "
        f"{youtube_rss.SCRAPETUBE_FAILURE_LIMIT}"
    )


def test_working_scrapetube_is_used_when_it_leads(monkeypatch):
    videos = [{"videoId": f"st-{i}"} for i in range(3)]
    fake = _fake_scrapetube(lambda: iter(videos))
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@Works/videos", limit=5,
        scrapetube_timeout=5.0, backends=("scrapetube", "rss"),
    )

    assert out == videos


def test_raising_scrapetube_still_falls_back(monkeypatch):
    def _boom():
        raise RuntimeError("IncompleteRead")

    fake = _fake_scrapetube(_boom)
    monkeypatch.setitem(sys.modules, "scrapetube", fake)
    monkeypatch.setattr(youtube_rss, "fetch_channel_videos_rss", _rss_stub)
    youtube_rss.reset_scrapetube_circuit()

    out = youtube_rss.fetch_channel_videos_with_fallback(
        "https://www.youtube.com/@Raises/videos", limit=5,
        scrapetube_timeout=5.0, backends=("scrapetube", "rss"),
    )

    assert out == RSS_VIDEOS
