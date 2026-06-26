"""Tests for reusing already-processed vault newsletter notes in the audio briefing."""
import os
import sys
import json
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from source_fetcher import SourceType
from vault_newsletters import load_vault_newsletter_items


def _make_note(d, subdir, name, date_str, title, body):
    nd = os.path.join(d, subdir)
    os.makedirs(nd, exist_ok=True)
    with open(os.path.join(nd, name), "w", encoding="utf-8") as f:
        f.write(f'---\ntitle: "{title}"\ndate_published: {date_str}\nurl: "http://x"\n---\n'
                f'← [[Log]]\n> {body}\n## Section\n{body} {body}\n')


def test_includes_recent_and_dedupes():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        _make_note(vault, "12-Batch", f"Batch-{today}.md", today, "Batch issue",
                   "Andrew Ng on loop engineering and shipping products with agents.")
        # first run: 1 item, correct shape
        items = load_vault_newsletter_items(data, vault)
        assert len(items) == 1
        it = items[0]
        assert it.source_name == "The Batch"
        assert it.source_type == SourceType.RSS
        assert "loop engineering" in it.summary.lower()
        assert "[[" not in it.summary and "##" not in it.summary  # cleaned
        # cache written
        assert os.path.exists(os.path.join(data, "voiced_newsletter_notes.json"))
        # second run: deduped -> 0
        assert load_vault_newsletter_items(data, vault) == []


def test_excludes_stale_issues():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        _make_note(vault, "15-DanGo", f"DanGo-{old}.md", old, "Old", "stale health tips " * 10)
        assert load_vault_newsletter_items(data, vault) == []  # outside lookback


def test_skips_log_index_files():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        nd = os.path.join(vault, "12-Batch")
        os.makedirs(nd)
        with open(os.path.join(nd, "Batch Log.md"), "w") as f:
            f.write("---\ntitle: Log\n---\nindex of issues " * 20)
        assert load_vault_newsletter_items(data, vault) == []
