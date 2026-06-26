"""Regression tests for the briefing-pipeline date sort.

Bug (2026-06): SourceFetcher.fetch_all_sources() sorted the merged item list
with `key=lambda x: x.published_date or datetime.min`. YouTube items carry
tz-naive dates ('X days ago' -> datetime.now()) while RSS items carry tz-aware
dates (dateparser on a feed pubDate). Sorting them together intermittently
raised `TypeError: can't compare offset-naive and offset-aware datetimes`,
which aborted the entire briefing before audio generation + Drive upload, so
days silently never landed in Drive.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from source_fetcher import _normalize_dt_for_compare, FetchedItem, SourceType


def _item(pd):
    return FetchedItem(
        title="t", url="u", content="c", source_name="s",
        source_type=SourceType.RSS, published_date=pd,
    )


def test_old_raw_key_crashed_on_mixed_tz():
    """Documents the original failure: the raw key raises on mixed tz."""
    aware = datetime.now(timezone.utc)
    naive = datetime.now()
    with pytest.raises(TypeError):
        # [aware, naive] forces the first comparison to mix awareness.
        sorted([_item(aware), _item(naive)],
               key=lambda x: x.published_date or datetime.min, reverse=True)


def test_normalized_key_sorts_mixed_tz_without_error():
    aware_new = datetime.now(timezone.utc)
    naive_old = datetime.now() - timedelta(days=3)
    aware_oldest = aware_new - timedelta(days=10)
    items = [_item(naive_old), _item(aware_new), _item(None), _item(aware_oldest)]

    items.sort(key=lambda x: _normalize_dt_for_compare(x.published_date), reverse=True)

    # newest-first: aware_new, naive_old, aware_oldest, then None (sorts oldest)
    assert items[0].published_date == aware_new
    assert items[-1].published_date is None


def test_normalize_strips_tz_and_converts_to_utc():
    # 12:00 at +02:00 == 10:00 UTC, naive
    aware = datetime(2026, 6, 13, 12, 0, tzinfo=timezone(timedelta(hours=2)))
    out = _normalize_dt_for_compare(aware)
    assert out.tzinfo is None
    assert out == datetime(2026, 6, 13, 10, 0)


def test_normalize_none_sorts_oldest():
    assert _normalize_dt_for_compare(None) == datetime.min


def test_normalize_passes_through_naive():
    naive = datetime(2026, 6, 13, 9, 0)
    assert _normalize_dt_for_compare(naive) == naive
