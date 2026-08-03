"""yt-dlp channel-listing backend (2026-08-03).

Added after both existing backends failed at once: scrapetube hangs
(YouTube-side breakage) and the RSS feed endpoint went to ~5% success with
failure runs of 5-10 consecutive requests. yt-dlp kept working throughout, so
it becomes the middle rung: RSS -> yt-dlp -> scrapetube.

Two measured facts drive the design:

  * yt-dlp's flat listing is cheap (~0.4s for 15 videos) but carries NO dates —
    `timestamp`, `upload_date` and `release_timestamp` are all None.
  * Resolving a real date costs ~1s per video.

That matters because of source_fetcher._fetch_youtube's filter:

    if pub_date and pub_date.date() < cutoff_date.date(): skip

The date test is *guarded on pub_date being truthy*, so a video with no date
is NOT filtered — it sails through and gets summarized however old it is. So
this backend must return only videos it has genuine dates for, and must bound
how many lookups it will pay for.
"""
import os
import sys
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import youtube_rss


DAY = 86400


def _fake_ytdlp(entries, video_meta, calls):
    """Stand-in `yt_dlp` module. `calls` records every extract_info URL."""
    mod = types.ModuleType("yt_dlp")

    class YoutubeDL:
        def __init__(self, opts=None):
            self.opts = opts or {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download=False):
            calls.append(url)
            if "watch?v=" in url:
                vid = url.split("watch?v=")[1]
                meta = video_meta.get(vid)
                if meta is None:
                    raise RuntimeError(f"unavailable: {vid}")
                return meta
            return {"channel": "Test Channel", "channel_id": "UCtest", "entries": entries}

    mod.YoutubeDL = YoutubeDL
    return mod


def _entries(n, prefix="vid"):
    return [{"id": f"{prefix}{i}", "title": f"Video {i}"} for i in range(n)]


def _meta(age_days, title="Video"):
    return {"timestamp": int(time.time() - age_days * DAY),
            "title": title, "channel": "Test Channel"}


def test_returns_dated_videos_in_the_shared_shape(monkeypatch):
    calls = []
    meta = {f"vid{i}": _meta(i, f"Video {i}") for i in range(3)}
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp(_entries(3), meta, calls))

    out = youtube_rss.fetch_channel_videos_ytdlp("https://www.youtube.com/@X/videos", limit=3)

    assert out is not None and len(out) == 3
    first = out[0]
    # Same dict shape scrapetube and RSS emit, so callers stay interchangeable.
    assert first["videoId"] == "vid0"
    assert first["title"]["runs"][0]["text"] == "Video 0"
    assert first["ownerText"]["runs"][0]["text"] == "Test Channel"
    assert first["publishedTimeText"]["simpleText"]  # non-empty "X ago"
    assert first["_publishedIso"]


def test_undated_videos_are_dropped(monkeypatch):
    # The pipeline treats a missing date as "keep", so an undated entry would be
    # summarized no matter how old. Dropping it is the only safe choice.
    calls = []
    meta = {
        "vid0": _meta(1),
        "vid1": {"title": "No date", "channel": "Test Channel"},  # no timestamp
        "vid2": _meta(2),
    }
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp(_entries(3), meta, calls))

    out = youtube_rss.fetch_channel_videos_ytdlp("https://www.youtube.com/@X/videos", limit=3)

    assert [v["videoId"] for v in out] == ["vid0", "vid2"]


def test_unavailable_video_does_not_sink_the_batch(monkeypatch):
    calls = []
    meta = {"vid0": _meta(1), "vid2": _meta(2)}  # vid1 missing -> extract raises
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp(_entries(3), meta, calls))

    out = youtube_rss.fetch_channel_videos_ytdlp("https://www.youtube.com/@X/videos", limit=3)

    assert [v["videoId"] for v in out] == ["vid0", "vid2"]


def test_date_lookups_are_capped(monkeypatch):
    # ~1s per lookup, so an unbounded listing would cost ~15s x 12 channels.
    calls = []
    meta = {f"vid{i}": _meta(0) for i in range(20)}
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp(_entries(20), meta, calls))

    out = youtube_rss.fetch_channel_videos_ytdlp(
        "https://www.youtube.com/@X/videos", limit=20, max_date_lookups=3
    )

    assert len(out) == 3
    video_calls = [c for c in calls if "watch?v=" in c]
    assert len(video_calls) == 3


def test_stops_early_once_clearly_past_the_window(monkeypatch):
    # Listings are newest-first, so once we're well past any daily cutoff there
    # is nothing left worth paying for.
    calls = []
    meta = {"vid0": _meta(1), "vid1": _meta(400), "vid2": _meta(401),
            "vid3": _meta(402), "vid4": _meta(403)}
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp(_entries(5), meta, calls))

    out = youtube_rss.fetch_channel_videos_ytdlp(
        "https://www.youtube.com/@X/videos", limit=5, max_age_days=30
    )

    video_calls = [c for c in calls if "watch?v=" in c]
    assert len(video_calls) < 5, "should not have priced every entry"
    assert [v["videoId"] for v in out] == ["vid0"]


def test_a_single_pinned_old_video_does_not_stop_the_scan(monkeypatch):
    # Channels pin videos, which puts an old one at position 0. Stopping at the
    # first old entry would return nothing at all for those channels.
    calls = []
    meta = {"vid0": _meta(400), "vid1": _meta(1), "vid2": _meta(2)}
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp(_entries(3), meta, calls))

    out = youtube_rss.fetch_channel_videos_ytdlp(
        "https://www.youtube.com/@X/videos", limit=3, max_age_days=30
    )

    assert [v["videoId"] for v in out] == ["vid1", "vid2"]


def test_returns_none_when_listing_fails(monkeypatch):
    mod = types.ModuleType("yt_dlp")

    class YoutubeDL:
        def __init__(self, opts=None): pass
        def __enter__(self): return self
        def __exit__(self, *exc): return False
        def extract_info(self, url, download=False):
            raise RuntimeError("channel unavailable")

    mod.YoutubeDL = YoutubeDL
    monkeypatch.setitem(sys.modules, "yt_dlp", mod)

    # None (not []) so the caller falls through to the next backend.
    assert youtube_rss.fetch_channel_videos_ytdlp("https://www.youtube.com/@X/videos") is None


def test_empty_listing_returns_none(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", _fake_ytdlp([], {}, []))
    assert youtube_rss.fetch_channel_videos_ytdlp("https://www.youtube.com/@X/videos") is None
