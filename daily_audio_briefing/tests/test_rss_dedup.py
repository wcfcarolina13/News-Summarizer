"""Regression tests for RSS/article items being re-delivered (2026-08-03).

Bug: the Aug 3 briefing was 54% verbatim Aug 2 content. Both repeated items
were RSS items dated Aug 2; the YouTube items were correctly deduped.

Two things compounded:
  * scheduler.py computes `cutoff = datetime.now() - timedelta(hours=24)`, but
    the RSS filter compares `pub_date.date() < cutoff_date.date()` — truncated
    to DATE granularity, which widens a 24h window to as much as 48h. Anything
    dated "yesterday" is in scope regardless of clock time.
  * RSS items had no dedup cache at all. Videos have processed_videos.json and
    local notes have voiced_newsletter_notes.json; RSS had nothing.

So any RSS item published before the previous run's clock time was re-read the
next day. Intermittent in practice — it only bites when a run lands late enough
to sweep up same-day items (the Aug 2 recovery ran at 18:45, so the Aug 3 run
re-read all of Aug 2).

Fix: articles get the same treatment videos already had — a cache keyed by URL,
committed only after delivery, so a failed run leaves them eligible for retry.
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import source_fetcher as sf_mod
from source_fetcher import SourceFetcher, SourceConfig, SourceType
from video_cache import load_cache, save_cache, CACHE_FILENAME, article_key


def _fetcher(tmp_path):
    return SourceFetcher(api_key="x", data_dir=str(tmp_path))


# --- cache layer -------------------------------------------------------------

def test_empty_cache_has_an_articles_bucket(tmp_path):
    assert load_cache(str(tmp_path)).get("articles") == {}


def test_legacy_cache_without_articles_still_loads(tmp_path):
    # The live processed_videos.json predates this bucket; it must not be
    # treated as corrupt (that would silently wipe every cached video).
    legacy = {"version": 1, "videos": {"vidA": {"processed_date": "2026-08-01"}}}
    with open(os.path.join(str(tmp_path), CACHE_FILENAME), "w") as fh:
        json.dump(legacy, fh)

    cache = load_cache(str(tmp_path))

    assert "vidA" in cache["videos"]
    assert cache.get("articles") == {}


def test_commit_article_urls_persists(tmp_path):
    n = SourceFetcher.commit_article_urls(str(tmp_path), ["https://x.test/a"])
    assert n == 1
    assert article_key("https://x.test/a") in load_cache(str(tmp_path))["articles"]


def test_commit_article_urls_ignores_empty(tmp_path):
    assert SourceFetcher.commit_article_urls(str(tmp_path), []) == 0


def test_article_key_normalises_incidental_url_differences():
    # Feeds are inconsistent about trailing slashes and fragments between runs;
    # treating those as different articles would defeat the cache.
    base = article_key("https://x.test/post")
    assert article_key("https://x.test/post/") == base
    assert article_key("https://x.test/post#section") == base
    assert article_key("  https://x.test/post  ") == base
    assert article_key("https://x.test/other") != base


def test_save_cache_prunes_stale_articles(tmp_path):
    old = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    fresh = datetime.now().strftime("%Y-%m-%d")
    save_cache(str(tmp_path), {"version": 1, "videos": {},
                               "articles": {"old": {"processed_date": old},
                                            "new": {"processed_date": fresh}}})

    articles = load_cache(str(tmp_path))["articles"]

    assert "new" in articles and "old" not in articles


# --- deferred commit, mirroring the video path -------------------------------

def test_deferred_articles_are_not_persisted_until_commit(tmp_path):
    f = _fetcher(tmp_path)
    f.defer_cache = True
    f._pending_articles.append("https://x.test/a")

    # A run that dies before delivery must leave the article eligible again.
    assert load_cache(str(tmp_path))["articles"] == {}


def test_commit_persists_videos_and_articles_together(tmp_path):
    f = _fetcher(tmp_path)
    f.defer_cache = True
    f._pending_processed.append("vid1")
    f._pending_articles.append("https://x.test/a")

    f.commit_processed_cache()

    cache = load_cache(str(tmp_path))
    assert "vid1" in cache["videos"]
    assert article_key("https://x.test/a") in cache["articles"]
    assert f._pending_articles == []


def test_stash_pending_articles_returns_a_copy(tmp_path):
    # The deferred-render path carries these in pending_render.json, because the
    # fetcher is gone by the time a later run delivers.
    f = _fetcher(tmp_path)
    f.defer_cache = True
    f._pending_articles.append("https://x.test/a")

    stashed = f.stash_pending_articles()
    stashed.append("https://x.test/mutated")

    assert f._pending_articles == ["https://x.test/a"]


# --- behaviour: the fetch actually skips ------------------------------------

_FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Test Feed</title>
<item><title>Already delivered</title><link>https://x.test/seen</link>
<description>old body</description><pubDate>Sat, 02 Aug 2026 06:00:00 GMT</pubDate></item>
<item><title>Brand new</title><link>https://x.test/fresh</link>
<description>new body</description><pubDate>Sun, 03 Aug 2026 06:00:00 GMT</pubDate></item>
</channel></rss>"""


class _Resp:
    content = _FEED.encode()
    text = _FEED
    def raise_for_status(self): pass


def test_fetch_rss_skips_already_delivered_articles(tmp_path, monkeypatch):
    SourceFetcher.commit_article_urls(str(tmp_path), ["https://x.test/seen"])

    f = _fetcher(tmp_path)
    monkeypatch.setattr(sf_mod, "requests", type("R", (), {"get": staticmethod(lambda *a, **k: _Resp())}))
    monkeypatch.setattr(SourceFetcher, "_summarize_article", lambda self, *a, **k: "summary")

    items = f._fetch_rss(
        SourceConfig(url="https://x.test/feed", source_type=SourceType.RSS),
        cutoff_date=datetime(2026, 1, 1), max_items=10, custom_instructions="",
    )

    urls = [i.url for i in items]
    assert "https://x.test/fresh" in urls
    assert "https://x.test/seen" not in urls, "already-delivered article was re-read"
