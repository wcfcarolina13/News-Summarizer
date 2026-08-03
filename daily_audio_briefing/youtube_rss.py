"""YouTube channel video listing via RSS — resilient fallback for scrapetube.

scrapetube parses YouTube's HTML+JSON ytInitialData blob, which YouTube changes
frequently and breaks the parser. The RSS feed at
    https://www.youtube.com/feeds/videos.xml?channel_id=UC...
is a stable, public XML endpoint that lists ~15 most recent videos with reliable
metadata (videoId, title, published timestamp, author).

This module exposes one function, ``fetch_channel_videos_rss(url, limit)``,
which returns videos in the same dict shape that scrapetube emits, so callers
can treat both backends interchangeably.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from typing import List, Optional
from xml.etree import ElementTree as ET

try:  # requests is in the desktop + server requirements; this should always work
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


_CHANNEL_ID_RE = re.compile(r'/channel/(UC[A-Za-z0-9_-]{20,})')
_CHANNEL_ID_JSON_RE = re.compile(r'"channelId"\s*:\s*"(UC[A-Za-z0-9_-]{20,})"')
_BROWSE_ID_JSON_RE = re.compile(r'"browseId"\s*:\s*"(UC[A-Za-z0-9_-]{20,})"')
# Canonical / og:url meta tags point at the actual page's channel — much more
# reliable than grepping for the first channelId in the page (which can be a
# suggested-channels link).
_CANONICAL_URL_RE = re.compile(
    r'<link\s+rel="canonical"\s+href="https?://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{20,})"',
    re.IGNORECASE,
)
_OG_URL_RE = re.compile(
    r'<meta\s+property="og:url"\s+content="https?://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{20,})"',
    re.IGNORECASE,
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Cache resolved handle->channelId for the lifetime of the process so we don't
# refetch the channel page every video on every run.
_channel_id_cache: dict[str, str] = {}

# --- scrapetube hang guard ---------------------------------------------------
# scrapetube passes no timeout= to its requests session, and nothing sets a
# global socket timeout, so a YouTube-side stall blocks in recv() forever — it
# never returns and never raises, which makes the try/except below useless.
# (2026-08: this wedged the whole daemon for ~33h and cost three days of
# briefings.) We run scrapetube on a throwaway daemon thread and abandon it if
# it overruns. The abandoned thread may stay blocked — a blocked thread cannot
# be killed from Python — but it is a daemon thread and the run continues.
SCRAPETUBE_TIMEOUT = 25.0
# Once scrapetube has hung this many times in a process, stop trying it: when
# it breaks it tends to break for every channel, and 12 channels x 25s is 5
# minutes of dead wall-clock added to every run.
SCRAPETUBE_FAILURE_LIMIT = 2

# RSS leads as of 2026-08-03. scrapetube broke YouTube-side — it hangs on some
# channels and returns empty on others — while the RSS feed answered in <1s for
# every channel tested. Leading with RSS turns the ~50s of dead wait (two hangs
# before the circuit opens) into a sub-second path; scrapetube stays as the
# fallback for channels RSS can't resolve. Flip to False if scrapetube recovers
# and the 15-video RSS ceiling starts to bite.
PREFER_RSS = True

# The feed endpoint flaps. On 2026-08-03 it returned HTTP 500 and HTTP 404 for a
# *valid* channel id (resolution verified against canonical/og:url/browseId)
# minutes after serving 15 videos for that same channel. Now that RSS leads, a
# single bad moment would empty a briefing section, so retry briefly first.
# 404 is retried too — during that incident it was not authoritative.
RSS_ATTEMPTS = 3
RSS_RETRY_BACKOFF = 1.5  # seconds, multiplied by attempt number

_scrapetube_timeouts = 0


def reset_scrapetube_circuit() -> None:
    """Re-arm scrapetube after the circuit has opened (also used by tests)."""
    global _scrapetube_timeouts
    _scrapetube_timeouts = 0


def _scrapetube_circuit_open() -> bool:
    return _scrapetube_timeouts >= SCRAPETUBE_FAILURE_LIMIT


def _fetch_via_scrapetube(channel_url: str, limit: int, timeout: float) -> dict:
    """Run scrapetube bounded by ``timeout``.

    Returns a dict with exactly one of: ``videos`` (list), ``error`` (exception),
    or ``timeout`` (True). Never raises.
    """
    outcome: dict = {}

    def _work():
        try:
            import scrapetube  # type: ignore
            outcome["videos"] = list(
                scrapetube.get_channel(channel_url=channel_url, limit=limit)
            )
        except BaseException as exc:  # noqa: BLE001 - must not escape the thread
            outcome["error"] = exc

    worker = threading.Thread(target=_work, daemon=True, name="scrapetube-fetch")
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        return {"timeout": True}
    return outcome


def _resolve_channel_id(channel_url: str, timeout: int = 15) -> Optional[str]:
    """Resolve a channel URL (any form) to its UC... channelId.

    Accepts: /channel/UC..., /@handle, /@handle/videos, /c/customname,
    /user/legacyname. Returns None if it can't be resolved.
    """
    if channel_url in _channel_id_cache:
        return _channel_id_cache[channel_url]

    # Direct hit: URL already contains the UC id.
    m = _CHANNEL_ID_RE.search(channel_url)
    if m:
        _channel_id_cache[channel_url] = m.group(1)
        return m.group(1)

    if requests is None:
        return None

    # Strip /videos, /streams, /featured suffixes — they redirect anyway, but
    # hitting the canonical handle URL is slightly cheaper.
    page_url = re.sub(r'/(videos|streams|featured|shorts|community|playlists)/?$', '', channel_url)
    page_url = page_url.split('?')[0].rstrip('/')

    try:
        resp = requests.get(page_url, headers=_DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except Exception:
        return None

    html = resp.text
    # Prefer canonical/og:url tags — these are the page's own self-identifying
    # channel id. Fall back to looser patterns only if those are absent.
    for pattern in (_CANONICAL_URL_RE, _OG_URL_RE, _CHANNEL_ID_JSON_RE, _CHANNEL_ID_RE, _BROWSE_ID_JSON_RE):
        m = pattern.search(html)
        if m:
            _channel_id_cache[channel_url] = m.group(1)
            return m.group(1)

    return None


def _humanize_age(iso_timestamp: str) -> str:
    """Convert an ISO 8601 timestamp into a 'X ago' string compatible with the
    existing _parse_youtube_date / dateparser logic ("3 hours ago", "1 day ago").
    """
    try:
        # Python 3.7+ accepts the trailing 'Z' only in 3.11+, so normalize.
        s = iso_timestamp.strip()
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        dt = datetime.fromisoformat(s)
    except Exception:
        return ""

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = max(1, seconds // 60)
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    days = seconds // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"


def fetch_channel_videos_rss(channel_url: str, limit: int = 20, timeout: int = 15) -> Optional[List[dict]]:
    """Fetch up to ``limit`` recent videos for a channel via RSS.

    Returns a list of dicts in the shape scrapetube emits, or None if anything
    goes wrong (so callers can decide how to handle that).

    Each returned dict contains:
        videoId             str
        title               {"runs": [{"text": <title>}]}
        publishedTimeText   {"simpleText": "<X ago>"}
        ownerText           {"runs": [{"text": <author>}]}
        _publishedIso       <ISO timestamp>     (extra field, not used by scrapetube)
    """
    if requests is None:
        return None

    channel_id = _resolve_channel_id(channel_url, timeout=timeout)
    if not channel_id:
        return None

    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    resp = None
    for attempt in range(1, RSS_ATTEMPTS + 1):
        try:
            resp = requests.get(feed_url, headers=_DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
            break
        except Exception:
            resp = None
            if attempt < RSS_ATTEMPTS:
                time.sleep(RSS_RETRY_BACKOFF * attempt)
    if resp is None:
        return None

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return None

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    videos: List[dict] = []
    for entry in root.findall("atom:entry", ns)[:limit]:
        vid = entry.findtext("yt:videoId", namespaces=ns) or ""
        title = entry.findtext("atom:title", namespaces=ns) or ""
        published = entry.findtext("atom:published", namespaces=ns) or ""
        author = entry.findtext("atom:author/atom:name", namespaces=ns) or ""
        if not vid:
            continue
        videos.append({
            "videoId": vid,
            "title": {"runs": [{"text": title}]},
            "publishedTimeText": {"simpleText": _humanize_age(published)},
            "ownerText": {"runs": [{"text": author}]},
            "_publishedIso": published,
        })
    return videos


def _attempt_rss(channel_url: str, limit: int, _log) -> Optional[List[dict]]:
    """RSS backend. Returns videos, or None if it produced nothing usable."""
    videos = fetch_channel_videos_rss(channel_url, limit=limit)
    if videos is None:
        # Either the channel id wouldn't resolve or the feed errored after all
        # RSS_ATTEMPTS. Don't claim the former — during the 2026-08-03 outage
        # ids resolved fine and the feed was what failed.
        _log(f"[YouTube/RSS] RSS returned no data for {channel_url} "
             f"(unresolved channel or feed error after {RSS_ATTEMPTS} attempts)")
        return None
    if not videos:
        _log(f"[YouTube/RSS] RSS returned 0 videos for {channel_url}")
        return None
    _log(f"[YouTube/RSS] RSS returned {len(videos)} videos for {channel_url}")
    return videos


def _attempt_scrapetube(channel_url: str, limit: int, timeout: float, _log) -> Optional[List[dict]]:
    """scrapetube backend, hard-bounded so it can never wedge the caller.

    Returns videos, or None if it hung, errored, or produced nothing.
    """
    global _scrapetube_timeouts

    if _scrapetube_circuit_open():
        _log(f"[YouTube/RSS] scrapetube circuit open ({_scrapetube_timeouts} hangs); skipping for {channel_url}")
        return None

    outcome = _fetch_via_scrapetube(channel_url, limit, timeout)
    if outcome.get("timeout"):
        _scrapetube_timeouts += 1
        _log(
            f"[YouTube/RSS] scrapetube timed out after {timeout:.0f}s for {channel_url} "
            f"(hang {_scrapetube_timeouts}/{SCRAPETUBE_FAILURE_LIMIT})"
        )
        return None
    if "error" in outcome:
        _log(f"[YouTube/RSS] scrapetube failed for {channel_url}: {outcome['error']}")
        return None

    videos = outcome.get("videos") or []
    if not videos:
        _log(f"[YouTube/RSS] scrapetube returned 0 videos for {channel_url}")
        return None
    _log(f"[YouTube/RSS] scrapetube returned {len(videos)} videos for {channel_url}")
    return videos


def fetch_channel_videos_with_fallback(
    channel_url: str,
    limit: int = 20,
    debug_log=None,
    scrapetube_timeout: Optional[float] = None,
    prefer_rss: bool = PREFER_RSS,
) -> List[dict]:
    """Fetch a channel's recent videos, trying both backends in order.

    Default order is RSS then scrapetube (see ``PREFER_RSS``). Whichever runs
    second only runs if the first produced no usable videos.

    ``debug_log`` is an optional callable (str) -> None for logging.
    ``scrapetube_timeout`` bounds the scrapetube attempt (default
    ``SCRAPETUBE_TIMEOUT``); without it a stalled read blocks forever.
    Always returns a list (possibly empty); never raises.

    Note: the RSS feed only ever exposes the ~15 most recent videos, whatever
    ``limit`` says. That covers any daily run comfortably, but a long backfill
    wanting more depth needs scrapetube — which is exactly what is broken.
    """
    def _log(msg: str):
        if debug_log:
            try:
                debug_log(msg)
            except Exception:
                pass

    timeout = SCRAPETUBE_TIMEOUT if scrapetube_timeout is None else scrapetube_timeout
    order = ("rss", "scrapetube") if prefer_rss else ("scrapetube", "rss")

    for backend in order:
        if backend == "rss":
            videos = _attempt_rss(channel_url, limit, _log)
        else:
            videos = _attempt_scrapetube(channel_url, limit, timeout, _log)
        if videos:
            return videos

    _log(f"[YouTube/RSS] both backends failed for {channel_url}")
    return []
