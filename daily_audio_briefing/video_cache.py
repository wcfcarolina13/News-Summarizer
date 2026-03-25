# Source Generated with Decompyle++
# File: video_cache.pyc (Python 3.12)

'''
Video Cache — Persistent tracking of processed YouTube video IDs.

Prevents cross-day duplication by recording which videos have already been
summarized. Used by source_fetcher.py to skip known videos before transcript
fetch (saving API calls and tokens).

Cache file: processed_videos.json (in data_dir, resolved by FileManager)
'''
import json
import logging
import os
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)
CACHE_FILENAME = 'processed_videos.json'
TTL_DAYS = 30

def _empty_cache():
    '''Return an empty cache structure.'''
    return {
        'version': 1,
        'videos': { } }


def load_cache(cache_dir = None):
    '''Load the processed videos cache from disk.

    Args:
        cache_dir: Directory containing processed_videos.json

    Returns:
        Cache dict with structure {"version": 1, "videos": {video_id: {...}}}
        Returns empty structure if file is missing, empty, or corrupt.
    '''
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    if not os.path.exists(cache_path):
        return _empty_cache()
# WARNING: Decompyle incomplete


def save_cache(cache_dir = None, cache_data = None):
    """Save the processed videos cache to disk with TTL cleanup.

    Drops entries where processed_date is more than TTL_DAYS ago.
    Creates cache_dir if it doesn't exist.

    Args:
        cache_dir: Directory to write processed_videos.json into
        cache_data: Cache dict to save
    """
    os.makedirs(cache_dir, exist_ok = True)
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)
    cutoff = datetime.now() - timedelta(days = TTL_DAYS)
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    cleaned_videos = { }
    for video_id, entry in cache_data.get('videos', { }).items():
        processed_date = entry.get('processed_date', '')
        if not processed_date >= cutoff_str:
            continue
        cleaned_videos[video_id] = entry
    cleaned_data = {
        'version': cache_data.get('version', 1),
        'videos': cleaned_videos }
# WARNING: Decompyle incomplete

