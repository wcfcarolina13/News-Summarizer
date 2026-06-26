"""Guard: the public repo must never track owner-personal config, and shippable code/config
must carry no owner PII marker. Prevents regressions of the public-readiness work.

The PII scan is intentionally scoped to SHIPPABLE code/config under the app dir (.py/.json/.txt) —
NOT prose docs (*.md) or repo-root notes, which may legitimately show example local paths and are a
separate, pre-existing concern."""
import os
import subprocess

# tests/ -> daily_audio_briefing/ -> repo root
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = "daily_audio_briefing"

PERSONAL_FILES = [
    f"{APP}/custom_instructions.txt",
    f"{APP}/channels.txt",
    f"{APP}/instruction_profiles.json",
    f"{APP}/voiced_newsletter_notes.json",
    f"{APP}/local_sources.json",
]

# Defined ONLY in this file; the scan skips this file, so the markers never need to appear in
# shippable code/config. (owner home path, email, ExecSum author id once in channels.txt.)
_FORBIDDEN_MARKERS = [
    "/Users/roti",
    "stoneba1992",
    "2e8f4f5d-5856-4463-ad71-a48cbba10c7a",
]
_SCAN_SUFFIXES = (".py", ".json", ".txt")  # shippable code/config/templates, not prose docs


def _tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def test_personal_files_not_tracked():
    tracked = set(_tracked_files())
    leaked = [f for f in PERSONAL_FILES if f in tracked]
    assert not leaked, f"personal files must not be tracked in a public repo: {leaked}"


def test_no_pii_markers_in_shippable_files():
    this_file = os.path.relpath(os.path.abspath(__file__), REPO)
    offenders = []
    for rel in _tracked_files():
        if rel == this_file:                      # defines the markers; skip itself
            continue
        if not rel.startswith(APP + "/"):         # only the app dir
            continue
        if not rel.endswith(_SCAN_SUFFIXES):      # only shippable code/config/templates
            continue
        try:
            with open(os.path.join(REPO, rel), "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except (OSError, UnicodeError):
            continue
        for marker in _FORBIDDEN_MARKERS:
            if marker in text:
                offenders.append((rel, marker))
    assert not offenders, f"PII markers found in shippable files: {offenders}"
