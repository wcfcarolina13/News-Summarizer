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
    try:
        resp = requests.get(feed_url, headers=_DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except Exception:
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


def fetch_channel_videos_with_fallback(
    channel_url: str,
    limit: int = 20,
    debug_log=None,
) -> List[dict]:
    """Try scrapetube first; if it returns 0 videos or errors, fall back to RSS.

    ``debug_log`` is an optional callable (str) -> None for logging.
    Always returns a list (possibly empty); never raises.
    """
    def _log(msg: str):
        if debug_log:
            try:
                debug_log(msg)
            except Exception:
                pass

    # Attempt 1: scrapetube
    try:
        import scrapetube  # type: ignore
        videos = list(scrapetube.get_channel(channel_url=channel_url, limit=limit))
        if videos:
            return videos
        _log(f"[YouTube/RSS] scrapetube returned 0 videos for {channel_url}; falling back to RSS")
    except Exception as e:
        _log(f"[YouTube/RSS] scrapetube failed for {channel_url}: {e}; falling back to RSS")

    # Attempt 2: RSS
    rss_videos = fetch_channel_videos_rss(channel_url, limit=limit)
    if rss_videos is None:
        _log(f"[YouTube/RSS] RSS fallback also failed for {channel_url}")
        return []
    _log(f"[YouTube/RSS] RSS fallback returned {len(rss_videos)} videos for {channel_url}")
    return rss_videos
