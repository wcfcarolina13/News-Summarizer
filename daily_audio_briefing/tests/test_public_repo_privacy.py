"""Privacy guard: tracked documentation must not leak a maintainer's home path.

The public repo (github.com/wcfcarolina13/News-Summarizer) is cloned by users
who should never see the maintainer's local macOS username or filesystem layout.
Prose docs are an easy place for a stray ``/Users/<name>/...`` path to slip in —
a pasted terminal line, an internal runbook, a hardcoded "file location".

This test scans every tracked Markdown and text file for macOS home paths and
fails with an actionable file:line list if any are found. Use ``~/...`` or a
repo-relative path instead. Shippable code/config (.py/.json) is intentionally
out of scope here — this guard is specifically about documentation prose.
"""
import re
import subprocess
from pathlib import Path

import pytest

# This file lives at <repo>/daily_audio_briefing/tests/, so the repo root is two
# directories up from daily_audio_briefing/.
REPO_ROOT = Path(__file__).resolve().parents[2]

# A real macOS home path is /Users/<segment>; <segment> is a username unless it
# is an obvious placeholder, which documentation may legitimately use.
_HOME_PATH = re.compile(r"/Users/([^/\s`]+)")
_PLACEHOLDERS = {"username", "yourname", "user", "you", "me"}


def _is_placeholder(segment):
    return segment.startswith("<") or segment.lower() in _PLACEHOLDERS


def _tracked_docs():
    """Tracked .md/.txt paths relative to the repo root; skip if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "*.md", "*.txt"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git unavailable; cannot enumerate tracked docs")
    return [p for p in result.stdout.split("\0") if p]


def test_docs_have_no_home_path_leak():
    offenders = []
    for rel in _tracked_docs():
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for segment in _HOME_PATH.findall(line):
                if not _is_placeholder(segment):
                    offenders.append(f"{rel}:{lineno}  /Users/{segment}")

    assert not offenders, (
        "Home-path leak in tracked docs (use ~/ or a repo-relative path):\n  "
        + "\n  ".join(offenders)
    )
