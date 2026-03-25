"""Tests for video_cache module."""
import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

# Add parent dir to path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from video_cache import load_cache, save_cache, _empty_cache, CACHE_FILENAME, TTL_DAYS


@pytest.fixture
def cache_dir():
    """Create a temporary directory for cache tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestEmptyCache:
    def test_structure(self):
        cache = _empty_cache()
        assert cache == {'version': 1, 'videos': {}}

    def test_returns_new_dict_each_call(self):
        a = _empty_cache()
        b = _empty_cache()
        assert a is not b
        assert a['videos'] is not b['videos']


class TestLoadCache:
    def test_missing_file(self, cache_dir):
        result = load_cache(cache_dir)
        assert result == _empty_cache()

    def test_empty_dir_string(self):
        result = load_cache("")
        assert result == _empty_cache()

    def test_none_dir(self):
        result = load_cache(None)
        assert result == _empty_cache()

    def test_valid_cache(self, cache_dir):
        data = {
            'version': 1,
            'videos': {
                'abc123': {'processed_date': '2026-03-20', 'title': 'Test Video'}
            }
        }
        with open(os.path.join(cache_dir, CACHE_FILENAME), 'w') as f:
            json.dump(data, f)

        result = load_cache(cache_dir)
        assert result['version'] == 1
        assert 'abc123' in result['videos']
        assert result['videos']['abc123']['title'] == 'Test Video'

    def test_corrupt_json(self, cache_dir):
        with open(os.path.join(cache_dir, CACHE_FILENAME), 'w') as f:
            f.write("not valid json {{{")

        result = load_cache(cache_dir)
        assert result == _empty_cache()

    def test_empty_file(self, cache_dir):
        with open(os.path.join(cache_dir, CACHE_FILENAME), 'w') as f:
            f.write("")

        result = load_cache(cache_dir)
        assert result == _empty_cache()

    def test_invalid_structure(self, cache_dir):
        with open(os.path.join(cache_dir, CACHE_FILENAME), 'w') as f:
            json.dump({"foo": "bar"}, f)

        result = load_cache(cache_dir)
        assert result == _empty_cache()


class TestSaveCache:
    def test_basic_save(self, cache_dir):
        data = {
            'version': 1,
            'videos': {
                'vid1': {'processed_date': datetime.now().strftime('%Y-%m-%d'), 'title': 'Recent'}
            }
        }
        save_cache(cache_dir, data)

        cache_path = os.path.join(cache_dir, CACHE_FILENAME)
        assert os.path.exists(cache_path)

        with open(cache_path, 'r') as f:
            saved = json.load(f)
        assert saved['version'] == 1
        assert 'vid1' in saved['videos']

    def test_ttl_cleanup(self, cache_dir):
        old_date = (datetime.now() - timedelta(days=TTL_DAYS + 5)).strftime('%Y-%m-%d')
        recent_date = datetime.now().strftime('%Y-%m-%d')

        data = {
            'version': 1,
            'videos': {
                'old_vid': {'processed_date': old_date, 'title': 'Old'},
                'new_vid': {'processed_date': recent_date, 'title': 'New'},
            }
        }
        save_cache(cache_dir, data)

        with open(os.path.join(cache_dir, CACHE_FILENAME), 'r') as f:
            saved = json.load(f)

        assert 'old_vid' not in saved['videos']
        assert 'new_vid' in saved['videos']

    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, 'sub', 'dir')
            data = {'version': 1, 'videos': {}}
            save_cache(nested, data)
            assert os.path.exists(os.path.join(nested, CACHE_FILENAME))

    def test_none_inputs(self):
        # Should not raise
        save_cache(None, None)
        save_cache("", None)
        save_cache(None, {'version': 1, 'videos': {}})

    def test_roundtrip(self, cache_dir):
        data = {
            'version': 1,
            'videos': {
                'v1': {'processed_date': datetime.now().strftime('%Y-%m-%d'), 'title': 'A'},
                'v2': {'processed_date': datetime.now().strftime('%Y-%m-%d'), 'title': 'B'},
            }
        }
        save_cache(cache_dir, data)
        loaded = load_cache(cache_dir)
        assert loaded['videos']['v1']['title'] == 'A'
        assert loaded['videos']['v2']['title'] == 'B'
        assert len(loaded['videos']) == 2
