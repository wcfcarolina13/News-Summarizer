"""Regression tests for deferred processed-videos caching.

Bug (2026-06): SourceFetcher saved newly-processed video IDs to the cache during
fetch, before the briefing was delivered. The failed Jun 12/13 runs summarized
~38 videos, cached them, then crashed at the sort — so those videos were stamped
'processed' but never spoken, and the next run skipped them as already-cached,
producing a stub briefing. Fix: defer the commit until delivery succeeds.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from source_fetcher import SourceFetcher
from video_cache import load_cache


def _fetcher(data_dir):
    return SourceFetcher(api_key="x", data_dir=str(data_dir))


def test_default_does_not_defer(tmp_path):
    f = _fetcher(tmp_path)
    assert f.defer_cache is False
    assert f.pending_cache_count() == 0


def test_deferred_ids_not_persisted_until_commit(tmp_path):
    f = _fetcher(tmp_path)
    f.defer_cache = True
    f._pending_processed.extend(["vid1", "vid2"])
    assert f.pending_cache_count() == 2
    # Nothing committed yet -> cache must not contain them (simulates a crash
    # before delivery: the videos stay eligible for the next run).
    assert "vid1" not in load_cache(str(tmp_path)).get("videos", {})


def test_commit_persists_and_clears(tmp_path):
    f = _fetcher(tmp_path)
    f.defer_cache = True
    f._pending_processed.extend(["vid1", "vid2"])
    assert f.commit_processed_cache() == 2
    assert f.pending_cache_count() == 0
    videos = load_cache(str(tmp_path))["videos"]
    assert "vid1" in videos and "vid2" in videos


def test_commit_is_idempotent(tmp_path):
    f = _fetcher(tmp_path)
    f.defer_cache = True
    f._pending_processed.append("vidA")
    assert f.commit_processed_cache() == 1
    # Second call with nothing pending is a no-op.
    assert f.commit_processed_cache() == 0
