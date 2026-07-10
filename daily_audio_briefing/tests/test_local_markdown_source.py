"""Tests for reusing already-summarized local markdown notes in the audio briefing."""
import os
import sys
import json
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from source_fetcher import SourceType
from local_markdown_source import load_local_markdown_items, commit_voiced_items


def _make_note(d, subdir, name, date_str, title, body):
    nd = os.path.join(d, subdir)
    os.makedirs(nd, exist_ok=True)
    with open(os.path.join(nd, name), "w", encoding="utf-8") as f:
        f.write(f'---\ntitle: "{title}"\ndate_published: {date_str}\nurl: "http://x"\n---\n'
                f'← [[Log]]\n> {body}\n## Section\n{body} {body}\n')


def _cfg(base_dir, subdir, source_name, **extra):
    folder = {"subdir": subdir, "source_name": source_name}
    folder.update(extra)
    return {"base_dir": base_dir, "folders": [folder], "lookback_days": 10}


def _write_raw(d, subdir, name, raw):
    nd = os.path.join(d, subdir)
    os.makedirs(nd, exist_ok=True)
    with open(os.path.join(nd, name), "w", encoding="utf-8") as f:
        f.write(raw)


def test_strips_read_only_artifacts_for_tts():
    """Connection Points block, meta preamble, citations, and raw URLs must not reach audio;
    a leading source-name prefix is stripped from the title."""
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        _write_raw(vault, "12-Batch", f"Batch-{today}.md",
            f'---\ntitle: "The Batch — {today}: Issue 1 — Loop Engineering"\ndate_published: {today}\n---\n'
            "# The Batch\n\n"
            "Items extracted from The Batch (Andrew Ng / deeplearning.ai), filtered for signal.\n\n"
            "← [[Batch Log]]\n\n"
            "> A real summary about loop engineering and shipping agents, long enough to keep.\n\n"
            "## A Section\n\n"
            "The model is freely accessible through biohub.ai/tools/fold and weights are public.\n\n"
            "*Reference:* O'Toole C.K. et al. Nature (2026). https://doi.org/10.1038/s41586-026-10524-5\n\n"
            "## Connection Points\n\n"
            "- [[Some Other Note]] — vault navigation that must never be read aloud\n")
        items = load_local_markdown_items(data, _cfg(vault, "12-Batch", "The Batch"))
        assert len(items) == 1
        s = items[0].summary
        assert "Connection Points" not in s and "vault navigation" not in s   # truncated
        assert "Items extracted from" not in s                                # meta dropped
        assert "doi.org" not in s and "biohub.ai/tools/fold" not in s         # URLs stripped
        assert "Reference:" not in s                                          # citation dropped
        assert "loop engineering" in s.lower()                               # real content kept
        # title de-dup: leading "The Batch —" removed, rest intact
        assert not items[0].title.lower().startswith("the batch")
        assert "Issue 1" in items[0].title


def test_url_strip_does_not_eat_prose():
    """Real URLs/DOIs are stripped, but slashed prose (and/or, 24/7, U.S./allies) survives."""
    from local_markdown_source import _clean_body
    body = ("See github.com/foo/bar and visit https://example.com/x now. "
            "But keep and/or, TTS/audio, U.S./allies, and 24/7 running.")
    out = _clean_body(body)
    assert "github.com/foo/bar" not in out and "example.com/x" not in out   # real links gone
    assert "and/or" in out and "TTS/audio" in out and "24/7" in out and "U.S./allies" in out


def test_includes_recent_and_dedupes():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        _make_note(vault, "12-Batch", f"Batch-{today}.md", today, "Batch issue",
                   "Andrew Ng on loop engineering and shipping products with agents.")
        cfg = _cfg(vault, "12-Batch", "The Batch")
        items = load_local_markdown_items(data, cfg)
        assert len(items) == 1
        it = items[0]
        assert it.source_name == "The Batch"
        assert it.source_type == SourceType.RSS
        assert "loop engineering" in it.summary.lower()
        assert "[[" not in it.summary and "##" not in it.summary  # cleaned
        assert os.path.exists(os.path.join(data, "voiced_newsletter_notes.json"))
        # second run: deduped -> 0
        assert load_local_markdown_items(data, cfg) == []


def test_defer_commit_survives_crash_before_delivery():
    """The cache-before-delivery guard (same class as the Jun 12-13 video bug).

    With defer_commit=True a load does NOT mark notes voiced: if the run dies before
    delivery (AI rewrite, TTS, Drive), the next run re-offers the same note instead of
    silently skipping its audio forever. Only commit_voiced_items() persists the cache.
    """
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        _make_note(vault, "12-Batch", f"Batch-{today}.md", today, "Batch issue",
                   "Andrew Ng on loop engineering and shipping products with agents.")
        cfg = _cfg(vault, "12-Batch", "The Batch")
        # load with defer: nothing persisted (simulates a crash after load)
        items = load_local_markdown_items(data, cfg, defer_commit=True)
        assert len(items) == 1
        assert not os.path.exists(os.path.join(data, "voiced_newsletter_notes.json"))
        # "next run" retries the same note — not lost
        retry = load_local_markdown_items(data, cfg, defer_commit=True)
        assert len(retry) == 1
        # delivery verdict arrives -> commit (mixed list: only local_markdown items count)
        assert commit_voiced_items(data, retry) == 1
        # now it's voiced-once: no more re-offers
        assert load_local_markdown_items(data, cfg, defer_commit=True) == []


def test_excludes_stale_issues():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        _make_note(vault, "15-DanGo", f"DanGo-{old}.md", old, "Old", "stale tips " * 20)
        assert load_local_markdown_items(data, _cfg(vault, "15-DanGo", "Dan Go")) == []


def test_skips_excluded_filenames():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        nd = os.path.join(vault, "12-Batch")
        os.makedirs(nd)
        with open(os.path.join(nd, "Batch Log.md"), "w") as f:
            f.write("---\ntitle: Log\n---\nindex of issues " * 20)
        assert load_local_markdown_items(data, _cfg(vault, "12-Batch", "The Batch")) == []


def test_works_with_arbitrary_folder_name():
    """Genericity: not tied to Pontus numbered dirs."""
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        _make_note(vault, "MyNotes", f"note-{today}.md", today, "My note",
                   "A generic summarized note about something interesting and useful today.")
        items = load_local_markdown_items(data, _cfg(vault, "MyNotes", "My Notes"))
        assert len(items) == 1 and items[0].source_name == "My Notes"


def test_min_chars_drops_short_notes():
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as data:
        today = datetime.now().strftime("%Y-%m-%d")
        _make_note(vault, "12-Batch", f"Batch-{today}.md", today, "Tiny", "short")
        assert load_local_markdown_items(data, _cfg(vault, "12-Batch", "The Batch")) == []


def test_disabled_when_no_base_dir_or_folders():
    with tempfile.TemporaryDirectory() as data:
        assert load_local_markdown_items(data, {}) == []
        assert load_local_markdown_items(
            data, {"base_dir": "/nonexistent/xyz",
                   "folders": [{"subdir": "x", "source_name": "X"}]}) == []
        with tempfile.TemporaryDirectory() as vault:
            assert load_local_markdown_items(data, {"base_dir": vault, "folders": []}) == []


def test_resolves_from_config_file(monkeypatch, tmp_path):
    """config=None path: read local_sources.json from data_dir, env cleared."""
    monkeypatch.delenv("LOCAL_MARKDOWN_DIR", raising=False)
    monkeypatch.delenv("PONTUS_VAULT_DIR", raising=False)
    vault = tmp_path / "vault"
    data = tmp_path / "data"
    (vault / "12-Batch").mkdir(parents=True)
    data.mkdir()
    today = datetime.now().strftime("%Y-%m-%d")
    _make_note(str(vault), "12-Batch", f"Batch-{today}.md", today, "Batch",
               "Generic summarized content long enough to pass the minimum length check today.")
    (data / "local_sources.json").write_text(json.dumps({
        "base_dir": str(vault),
        "folders": [{"subdir": "12-Batch", "source_name": "The Batch"}],
    }))
    items = load_local_markdown_items(str(data))  # config=None -> resolve from file
    assert len(items) == 1 and items[0].source_name == "The Batch"


def test_env_override_takes_precedence(monkeypatch, tmp_path):
    """PONTUS_VAULT_DIR (back-compat) overrides config base_dir; LOCAL_MARKDOWN_DIR also works."""
    vault = tmp_path / "realvault"
    data = tmp_path / "data"
    (vault / "12-Batch").mkdir(parents=True)
    data.mkdir()
    today = datetime.now().strftime("%Y-%m-%d")
    _make_note(str(vault), "12-Batch", f"Batch-{today}.md", today, "Batch",
               "Generic summarized content long enough to pass the minimum length check today.")
    (data / "local_sources.json").write_text(json.dumps({
        "base_dir": "/nonexistent/bogus",
        "folders": [{"subdir": "12-Batch", "source_name": "The Batch"}],
    }))
    monkeypatch.delenv("LOCAL_MARKDOWN_DIR", raising=False)
    monkeypatch.setenv("PONTUS_VAULT_DIR", str(vault))
    items = load_local_markdown_items(str(data))
    assert len(items) == 1 and items[0].source_name == "The Batch"
