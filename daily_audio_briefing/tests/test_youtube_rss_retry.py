"""RSS feed must survive a flapping YouTube endpoint (2026-08-03).

Observed while promoting RSS to the primary backend: the feed endpoint returned
HTTP 500 and HTTP 404 for a *valid* channel id (resolution was correct —
canonical, og:url and browseId all agreed) within minutes of serving 15 videos
for the same channel. It is degraded and intermittent, not dead.

A single-shot fetch turns one bad moment into an empty briefing section, so the
feed fetch retries a couple of times before giving up. Giving up still returns
None, which lets the caller fall through to scrapetube.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import youtube_rss


FEED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>vid001</yt:videoId>
    <title>A Test Video</title>
    <published>2026-08-02T12:00:00+00:00</published>
    <author><name>Test Channel</name></author>
  </entry>
</feed>
"""

# Already contains the UC id, so _resolve_channel_id short-circuits without network.
CHANNEL_URL = "https://www.youtube.com/channel/UCqcbQf6yw5KzRoDDcZ_wBSw"


class _Resp:
    def __init__(self, status, content=b""):
        self.status_code = status
        self.content = content
        self.text = content.decode("utf-8", "replace")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _scripted_get(statuses):
    """requests.get stub that walks `statuses`, recording how many calls it saw."""
    calls = {"n": 0}

    def _get(url, **kwargs):
        i = calls["n"]
        calls["n"] += 1
        status = statuses[min(i, len(statuses) - 1)]
        return _Resp(status, FEED_XML if status == 200 else b"error")

    return _get, calls


def test_transient_500_then_success_returns_videos(monkeypatch):
    get, calls = _scripted_get([500, 200])
    monkeypatch.setattr(youtube_rss.requests, "get", get)
    monkeypatch.setattr(youtube_rss.time, "sleep", lambda *_: None)  # no real backoff

    videos = youtube_rss.fetch_channel_videos_rss(CHANNEL_URL, limit=5)

    assert videos is not None, "a transient 500 must not sink the whole fetch"
    assert len(videos) == 1
    assert videos[0]["videoId"] == "vid001"
    assert calls["n"] == 2


def test_transient_404_is_also_retried(monkeypatch):
    # A valid channel returned 404 during the incident, so 404 is not treated
    # as permanently authoritative here.
    get, calls = _scripted_get([404, 200])
    monkeypatch.setattr(youtube_rss.requests, "get", get)
    monkeypatch.setattr(youtube_rss.time, "sleep", lambda *_: None)

    videos = youtube_rss.fetch_channel_videos_rss(CHANNEL_URL, limit=5)

    assert videos is not None
    assert calls["n"] == 2


def test_persistent_failure_gives_up_and_returns_none(monkeypatch):
    get, calls = _scripted_get([500])
    monkeypatch.setattr(youtube_rss.requests, "get", get)
    monkeypatch.setattr(youtube_rss.time, "sleep", lambda *_: None)

    videos = youtube_rss.fetch_channel_videos_rss(CHANNEL_URL, limit=5)

    # None (not []) so the caller knows to try scrapetube.
    assert videos is None
    assert calls["n"] == youtube_rss.RSS_ATTEMPTS


def test_success_on_first_try_does_not_retry(monkeypatch):
    get, calls = _scripted_get([200])
    monkeypatch.setattr(youtube_rss.requests, "get", get)
    monkeypatch.setattr(youtube_rss.time, "sleep", lambda *_: None)

    videos = youtube_rss.fetch_channel_videos_rss(CHANNEL_URL, limit=5)

    assert videos and len(videos) == 1
    assert calls["n"] == 1, "a healthy feed must cost exactly one request"
