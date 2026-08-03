"""The deferred-render manifest must carry article URLs too (2026-08-03).

When the GPU gate holds back a render, the original fetcher is gone by the time
a later run delivers, so the deferred-commit IDs ride in pending_render.json and
commit on delivery. Videos and voiced notes were already carried; articles were
not, because they had no cache until now.

Without this, a deferred render would deliver its articles and then leave them
uncached — so the next run re-reads and re-speaks them. That is exactly the bug
the article cache exists to fix, just displaced into the resume path.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import scheduler as scheduler_mod
from scheduler import Scheduler
from video_cache import load_cache, article_key


class _StubFetcher:
    def __init__(self, videos, articles):
        self._v, self._a = videos, articles

    def stash_pending_cache(self):
        return list(self._v)

    def stash_pending_articles(self):
        return list(self._a)


def _scheduler(tmp_path):
    return Scheduler(data_dir=str(tmp_path))


def test_manifest_records_article_urls(tmp_path):
    s = _scheduler(tmp_path)
    today = dt.date(2026, 8, 3)
    fetcher = _StubFetcher(["vid1"], ["https://x.test/a"])

    s._pipeline_write_render_manifest(str(tmp_path), today, fetcher, [], "t")

    with open(s._render_manifest_path(str(tmp_path))) as fh:
        manifest = json.load(fh)
    assert manifest["video_ids"] == ["vid1"]
    assert manifest["article_urls"] == ["https://x.test/a"]


def test_manifest_without_a_fetcher_still_writes(tmp_path):
    # The upload-only retry path passes fetcher=None.
    s = _scheduler(tmp_path)
    s._pipeline_write_render_manifest(str(tmp_path), dt.date(2026, 8, 3), None, [], "t")

    with open(s._render_manifest_path(str(tmp_path))) as fh:
        manifest = json.load(fh)
    assert manifest["article_urls"] == []


def test_commit_persists_carried_articles(tmp_path):
    s = _scheduler(tmp_path)
    today = dt.date(2026, 8, 3)
    s._pipeline_write_render_manifest(
        str(tmp_path), today, _StubFetcher(["vid1"], ["https://x.test/a"]), [], "t")

    s._pipeline_commit_render_manifest(str(tmp_path), today, "t")

    cache = load_cache(str(tmp_path))
    assert "vid1" in cache["videos"]
    assert article_key("https://x.test/a") in cache["articles"]


def test_stale_manifest_does_not_stamp_articles(tmp_path):
    # A manifest from another day must not mark today's content delivered.
    s = _scheduler(tmp_path)
    s._pipeline_write_render_manifest(
        str(tmp_path), dt.date(2026, 8, 2),
        _StubFetcher(["vid1"], ["https://x.test/a"]), [], "t")

    s._pipeline_commit_render_manifest(str(tmp_path), dt.date(2026, 8, 3), "t")

    assert load_cache(str(tmp_path))["articles"] == {}
    assert not os.path.exists(s._render_manifest_path(str(tmp_path)))


def test_fetcher_lacking_the_new_method_still_yields_a_manifest(tmp_path):
    # The write is wrapped in try/except, so an AttributeError on one field
    # would discard the whole manifest and lose the video IDs with it —
    # silently reintroducing exactly the duplication this prevents.
    class _OldFetcher:
        def stash_pending_cache(self):
            return ["vid1"]

    s = _scheduler(tmp_path)
    today = dt.date(2026, 8, 3)

    s._pipeline_write_render_manifest(str(tmp_path), today, _OldFetcher(), [], "t")

    with open(s._render_manifest_path(str(tmp_path))) as fh:
        manifest = json.load(fh)
    assert manifest["video_ids"] == ["vid1"]
    assert manifest["article_urls"] == []


def test_legacy_manifest_without_article_urls_is_tolerated(tmp_path):
    # A manifest written by the previous build is still live on disk during the
    # upgrade; it must commit its videos, not blow up on the missing key.
    s = _scheduler(tmp_path)
    today = dt.date(2026, 8, 3)
    with open(s._render_manifest_path(str(tmp_path)), "w") as fh:
        json.dump({"date": today.isoformat(), "video_ids": ["vidLegacy"],
                   "note_paths": []}, fh)

    s._pipeline_commit_render_manifest(str(tmp_path), today, "t")

    assert "vidLegacy" in load_cache(str(tmp_path))["videos"]
