# Recovery Handoff — News Summarizer Source Repo

**Date:** 2026-03-25
**What happened:** The source repo at `/Users/roti/pontus/News-Summarizer-new` was a symlink to `/Users/roti/gemini_projects/News-Summarizer-new`. The gemini_projects copy was deleted via `rm -rf`, destroying the git repo with all commits from Mar 2–25. A fresh clone from GitHub (Mar 2 state) now sits at the same path.

## What's Working

The **deployed app** at `/Applications/Daily Audio Briefing.app` is running correctly with ALL fixes compiled in. It was built from the source before deletion and contains:

1. Video dedup cache (`video_cache.py`) — prevents same YouTube videos across days
2. Drive SSL retry with 3x backoff (`drive_manager.py`)
3. Filename rename (`2026-03-25_News.mp3` format)
4. Pipeline checkpoint awareness (skip fetch/summarize/TTS if output exists)
5. `_pipeline_drive_upload()` helper with error reason surfacing
6. Reading List to Audio dialog (gui_app.py)
7. Local Storage dialog (gui_app.py)
8. API timeout wrapper (api_usage_tracker.py)

**The app does NOT need rebuilding.** Only the source repo needs recovery.

## What Needs Recovery

The source repo at `/Users/roti/pontus/News-Summarizer-new/` is a fresh GitHub clone (commit `2029ade`, Mar 2 2026). It's missing all changes from Mar 2–25.

### Files that decompiled cleanly (can copy directly)

These were extracted from the frozen app via `pyinstxtractor-ng` + `pycdc` and have zero artifacts:

| File | Location | Lines |
|------|----------|-------|
| `video_cache.py` | `/tmp/recovered_source/video_cache.py` | 68 |
| `drive_manager.py` | `/tmp/recovered_source/drive_manager.py` | 355 |
| `api_usage_tracker.py` | `/tmp/recovered_source/api_usage_tracker.py` | 248 |
| `file_manager.py` | `/tmp/recovered_source/file_manager.py` | 99 |
| `audio_generator.py` | `/tmp/recovered_source/audio_generator.py` | 126 |
| `cloud_scheduler_client.py` | `/tmp/recovered_source/cloud_scheduler_client.py` | 125 |
| `voice_manager.py` | `/tmp/recovered_source/voice_manager.py` | 43 |

**Action:** Copy these into `daily_audio_briefing/`, verify they import cleanly, commit.

### Files that need manual re-application (decompiled with artifacts)

These have `<NODE:12>` artifacts on dataclass definitions and scattered syntax errors:

| File | Issue | Fix strategy |
|------|-------|-------------|
| `scheduler.py` | 1 `<NODE:12>` (ScheduledTask dataclass) + scattered decompiler errors | Start from GitHub base, re-apply changes using specs below |
| `source_fetcher.py` | 3 `<NODE:12>` (FetchedItem, SourceConfig, ArchiveLink) + errors | Start from GitHub base, re-apply changes using specs below |

**Specs documenting the exact changes:**
- `docs/superpowers/specs/2026-03-20-cross-day-video-dedup-design.md` — video cache integration
- `docs/superpowers/plans/2026-03-20-cross-day-video-dedup.md` — step-by-step with OLD/NEW code blocks

**Changes to re-apply to `scheduler.py` (GitHub base → current):**
1. Add `data_dir` parameter to `SourceFetcher()` call (~line 946): `data_dir=data_dir`
2. Add checkpoint block after `data_dir = fm.base_dir` (~line 895): compute `summary_path`/`audio_path` with new naming, check if exists, skip to Drive upload
3. Rename output files: `f"{today.isoformat()}_News.txt"` instead of `f"{safe_name}_W{week}_{today.isoformat()}.txt"`
4. Extract `_pipeline_drive_upload()` helper method from inline Drive upload code
5. Surface error reasons in Drive upload (`drive_error_msg = f"txt: {txt_result.get('reason', 'unknown')}"`)
6. Load custom instructions in pipeline (youtube_instructions, article_instructions) — check if this is already in GitHub base

**Changes to re-apply to `source_fetcher.py` (GitHub base → current):**
1. Add `data_dir` parameter to `__init__()`: `data_dir: str = ""`
2. Add `from video_cache import load_cache, save_cache` at top
3. In `_fetch_youtube()`: load cache, add `videos_skipped_by_cache` counter, check cache before transcript fetch, track newly processed videos, batch write-back after loop, add skip counter to summary log

### gui_app.py patch (Reading List + Local Storage features)

**Patch file:** `/tmp/gui_full_diff.patch` (831 lines)
- Applies cleanly to the GitHub base gui_app.py
- Contains: Reading List to Audio dialog, Local Storage dialog, button wiring
- **Action:** `git apply /tmp/gui_full_diff.patch`

### Other files with changes between Mar 2–25

These may have changes that aren't captured in the decompiled versions. Compare decompiled output against GitHub base to identify drift:
- `get_youtube_news.py` — disfluency fix was applied here too
- `execsum_processor.py` — may have changes
- `data_csv_processor.py` — may have changes
- `scheduler_daemon.py` — may have changes
- `make_audio_quality.py` — may have changes

**Strategy:** For each, compare `/tmp/recovered_source/{name}.py` against the GitHub base. If the decompiled version differs significantly from GitHub, it has changes that need investigating. If only cosmetic differences (comments stripped, formatting), the GitHub base is fine.

## Files in /tmp (EPHEMERAL — copy before reboot)

These will be lost on reboot:

```
/tmp/recovered_source/           — all decompiled .py files
/tmp/gui_full_diff.patch         — gui_app.py Reading List patch (831 lines)
/tmp/api_tracker_migration.patch — api_usage_tracker patch (45 lines)
/tmp/Daily Audio Briefing_extracted/ — full pyinstxtractor output with .pyc files
/tmp/pycdc/pycdc                 — compiled decompiler binary
```

**Action:** Copy `/tmp/recovered_source/` and `/tmp/*.patch` to a permanent location FIRST.

## Verification After Recovery

1. All modules import cleanly: `python3 -c "from scheduler import Scheduler; from source_fetcher import SourceFetcher; from video_cache import load_cache; print('OK')"`
2. Tests pass: `python3 -m pytest daily_audio_briefing/tests/test_video_cache.py -v`
3. App still runs (do NOT rebuild unless changes are verified — current app works)

## Guardrails Added

Two new CRITICAL guardrails in `/Users/roti/pontus/memory/guardrails.md`:
1. **ALWAYS Move to Trash, Never rm -rf** — use `mv <path> ~/.Trash/` for all deletions
2. **ALWAYS Check for Symlinks Before Deleting Directories** — run `readlink` and `file` before any deletion

## Symlink Warning

`/Users/roti/gemini_projects/` and `/Users/roti/pontus/` contain many directories with the same names. Some may be symlinks to each other. Before touching ANY directory in either location, check for symlinks first. Known symlink: `gemini_projects/Clawtex -> /Users/roti/pontus/pontus-forge`.
