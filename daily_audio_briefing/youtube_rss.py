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
from datetime import datetime, timedelta, timezone
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

# The feed endpoint flaps. On 2026-08-03 it returned HTTP 500 and HTTP 404 for a
# *valid* channel id (resolution verified against canonical/og:url/browseId)
# minutes after serving 15 videos for that same channel. Now that RSS leads, a
# single bad moment would empty a briefing section, so retry briefly first.
# 404 is retried too — during that incident it was not authoritative.
RSS_ATTEMPTS = 3
RSS_RETRY_BACKOFF = 1.5  # seconds, multiplied by attempt number

# --- yt-dlp backend ----------------------------------------------------------
# Added 2026-08-03, when scrapetube (hanging) and the RSS feed (~5% success,
# failure runs of 5-10) were both failing at once and yt-dlp was the only
# YouTube path still working.
#
# yt-dlp's flat channel listing is cheap (~0.4s/15 videos) but carries NO dates:
# timestamp, upload_date and release_timestamp are all None. A real date costs a
# per-video extract (~1s). We pay for those deliberately, because
# source_fetcher._fetch_youtube filters with
#     if pub_date and pub_date.date() < cutoff_date.date(): skip
# — guarded on pub_date being truthy, so an undated video is NOT filtered and
# would be summarized however old it is. Undated entries are therefore dropped.
YTDLP_MAX_DATE_LOOKUPS = 8   # hard cost ceiling: ~8s worst case per channel
YTDLP_MAX_AGE_DAYS = 21      # comfortably past any daily cutoff
YTDLP_STOP_AFTER_OLD = 2     # consecutive old entries before giving up (pinned-video tolerance)
YTDLP_SOCKET_TIMEOUT = 15    # never leave a socket unbounded again

DEFAULT_BACKENDS = ("rss", "ytdlp", "scrapetube")

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


def _ytdlp_published_iso(meta: dict) -> Optional[str]:
    """Pull a real publication timestamp out of a yt-dlp video info dict."""
    ts = meta.get("timestamp") or meta.get("release_timestamp")
    if ts:
        try:
            return datetime.fromtimestamp(int(ts), timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            pass
    upload_date = meta.get("upload_date")  # 'YYYYMMDD'
    if upload_date:
        try:
            return datetime.strptime(str(upload_date), "%Y%m%d").replace(
                tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return None


def fetch_channel_videos_ytdlp(
    channel_url: str,
    limit: int = 20,
    max_date_lookups: int = YTDLP_MAX_DATE_LOOKUPS,
    max_age_days: int = YTDLP_MAX_AGE_DAYS,
) -> Optional[List[dict]]:
    """List a channel's recent videos via yt-dlp.

    Returns videos in the same dict shape scrapetube and RSS emit, or None if
    the channel couldn't be listed at all (so the caller falls through).

    Only videos with a genuine date are returned — see the module constants for
    why an undated entry is dangerous. Date resolution costs ~1s per video, so
    it is bounded twice: at most ``max_date_lookups`` lookups, and it stops
    early once ``YTDLP_STOP_AFTER_OLD`` consecutive entries are older than
    ``max_age_days`` (listings are newest-first, but channels pin videos, so a
    single old entry must not end the scan).
    """
    try:
        import yt_dlp  # type: ignore
    except Exception:
        return None

    base_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": YTDLP_SOCKET_TIMEOUT,
    }

    try:
        with yt_dlp.YoutubeDL({**base_opts, "extract_flat": "in_playlist",
                               "playlistend": limit}) as ydl:
            listing = ydl.extract_info(channel_url, download=False)
    except Exception:
        return None

    entries = [e for e in ((listing or {}).get("entries") or []) if e]
    if not entries:
        return None

    channel_name = (listing or {}).get("channel") or (listing or {}).get("uploader") or ""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    videos: List[dict] = []
    consecutive_old = 0
    lookups = 0

    for entry in entries:
        if lookups >= max_date_lookups or consecutive_old >= YTDLP_STOP_AFTER_OLD:
            break
        vid = entry.get("id")
        if not vid:
            continue

        lookups += 1
        try:
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                meta = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={vid}", download=False)
        except Exception:
            # Deleted/private/geo-blocked video — skip it, keep the batch.
            continue

        meta = meta or {}
        published = _ytdlp_published_iso(meta)
        if not published:
            # No date means the pipeline's filter can't exclude it, so drop it.
            continue

        try:
            published_dt = datetime.fromisoformat(published)
        except ValueError:
            continue

        if published_dt < cutoff:
            consecutive_old += 1
            continue
        consecutive_old = 0

        videos.append({
            "videoId": vid,
            "title": {"runs": [{"text": meta.get("title") or entry.get("title") or ""}]},
            "publishedTimeText": {"simpleText": _humanize_age(published)},
            "ownerText": {"runs": [{"text": meta.get("channel") or channel_name}]},
            "_publishedIso": published,
        })

    return videos or None


def _attempt_ytdlp(channel_url: str, limit: int, _log) -> Optional[List[dict]]:
    """yt-dlp backend. Returns videos, or None if it produced nothing usable."""
    try:
        videos = fetch_channel_videos_ytdlp(channel_url, limit=limit)
    except Exception as exc:  # defensive: this path must never raise
        _log(f"[YouTube/RSS] yt-dlp failed for {channel_url}: {exc}")
        return None
    if not videos:
        _log(f"[YouTube/RSS] yt-dlp returned no dated videos for {channel_url}")
        return None
    _log(f"[YouTube/RSS] yt-dlp returned {len(videos)} videos for {channel_url}")
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
    backends: tuple = DEFAULT_BACKENDS,
) -> List[dict]:
    """Fetch a channel's recent videos, trying each backend in order.

    Default order is ``DEFAULT_BACKENDS`` — RSS, then yt-dlp, then scrapetube.
    RSS leads because it is by far the cheapest when healthy (<1s). yt-dlp sits
    ahead of scrapetube because scrapetube is the one that hangs. Each backend
    runs only if the previous produced no usable videos.

    ``debug_log`` is an optional callable (str) -> None for logging.
    ``scrapetube_timeout`` bounds the scrapetube attempt (default
    ``SCRAPETUBE_TIMEOUT``); without it a stalled read blocks forever.
    Always returns a list (possibly empty); never raises.

    Depth limits worth knowing for backfills: RSS only ever exposes the ~15 most
    recent videos whatever ``limit`` says, and the yt-dlp backend resolves at
    most ``YTDLP_MAX_DATE_LOOKUPS`` dates per channel. Both cover a daily run
    comfortably; deep history needs scrapetube, which is what is broken.
    """
    def _log(msg: str):
        if debug_log:
            try:
                debug_log(msg)
            except Exception:
                pass

    timeout = SCRAPETUBE_TIMEOUT if scrapetube_timeout is None else scrapetube_timeout

    for backend in backends:
        if backend == "rss":
            videos = _attempt_rss(channel_url, limit, _log)
        elif backend == "ytdlp":
            videos = _attempt_ytdlp(channel_url, limit, _log)
        elif backend == "scrapetube":
            videos = _attempt_scrapetube(channel_url, limit, timeout, _log)
        else:
            continue
        if videos:
            return videos

    _log(f"[YouTube/RSS] all backends failed for {channel_url}")
    return []
