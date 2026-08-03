"""
Delivered-content cache — persistent tracking of what has already been spoken.

Prevents cross-day duplication by recording which items have already been
summarized and delivered. Used by source_fetcher.py to skip known content
before transcript fetch / summarization (saving API calls and tokens).

Two buckets:
  videos   — YouTube video IDs
  articles — RSS/article URLs (added 2026-08-03, after the Aug 3 briefing came
             out 54% verbatim-identical to Aug 2: the date filter truncates to
             date granularity, so a 24h window can span 48h, and articles had
             no dedup at all while videos did)

Cache file: processed_videos.json (in data_dir, resolved by FileManager). The
filename is historical — it holds both buckets now.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger(__name__)
CACHE_FILENAME = 'processed_videos.json'
TTL_DAYS = 30


def _empty_cache():
    """Return an empty cache structure."""
    return {
        'version': 1,
        'videos': {},
        'articles': {}
    }


def article_key(url):
    """Normalise an article URL into a stable cache key.

    Feeds are inconsistent between runs about trailing slashes and fragments,
    and treating those as distinct articles would defeat the cache. Query
    strings are kept — they often carry the actual article identity.
    """
    if not url:
        return ''
    try:
        parts = urlsplit(str(url).strip())
        path = parts.path.rstrip('/') or '/'
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ''))
    except ValueError:
        return str(url).strip()


def load_cache(cache_dir=None):
    """Load the processed videos cache from disk.

    Args:
        cache_dir: Directory containing processed_videos.json

    Returns:
        Cache dict with structure {"version": 1, "videos": {video_id: {...}}}
        Returns empty structure if file is missing, empty, or corrupt.
    """
    if not cache_dir:
        return _empty_cache()
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    if not os.path.exists(cache_path):
        return _empty_cache()
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or 'videos' not in data:
            logger.warning("Cache file has invalid structure, returning empty cache")
            return _empty_cache()
        # Caches written before the articles bucket existed are valid, not
        # corrupt — backfill the key rather than discarding every cached video.
        data.setdefault('articles', {})
        return data
    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.warning(f"Failed to load cache: {e}")
        return _empty_cache()


def save_cache(cache_dir=None, cache_data=None):
    """Save the processed videos cache to disk with TTL cleanup.

    Drops entries where processed_date is more than TTL_DAYS ago.
    Creates cache_dir if it doesn't exist.

    Args:
        cache_dir: Directory to write processed_videos.json into
        cache_data: Cache dict to save
    """
    if not cache_dir or not cache_data:
        return
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cutoff = datetime.now() - timedelta(days=TTL_DAYS)
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    def _prune(bucket):
        return {k: v for k, v in bucket.items()
                if v.get('processed_date', '') >= cutoff_str}

    cleaned_videos = _prune(cache_data.get('videos', {}))
    cleaned_articles = _prune(cache_data.get('articles', {}))
    cleaned_data = {
        'version': cache_data.get('version', 1),
        'videos': cleaned_videos,
        'articles': cleaned_articles
    }
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2)
        logger.debug(
            f"Saved cache with {len(cleaned_videos)} videos / "
            f"{len(cleaned_articles)} articles to {cache_path}")
    except (IOError, OSError) as e:
        logger.error(f"Failed to save cache: {e}")
