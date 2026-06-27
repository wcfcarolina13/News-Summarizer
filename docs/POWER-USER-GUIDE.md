# Power User Guide — Architecture, Seams, and AI-Assisted Customization

This guide is for developers and technical users who want to understand how the pipeline works,
where to hook in new behavior, and how to use an AI assistant to extend the app safely.

---

## Architecture at a glance

```
sources.json / channels.txt
         │
         ▼
  load_sources()                    source_fetcher.py — builds SourceConfig list
         │
         ▼
  SourceFetcher.fetch_all_sources()  fetch transcripts (YouTube), parse feeds (RSS),
         │                           scrape archives (newsletter)
         │                           └─ each item summarized via the free LLM fallback chain
         │                              (llm_fallback.py) using custom_instructions as a
         │                              mandatory filter
         ▼
  format_items_for_audio()           source_fetcher.py — combine into a single narration script
         │
         ▼
  TTS                                make_audio_fast.py (gTTS) or make_audio_quality.py (Kokoro)
         │
         ▼
  Deliver                            scheduled pipeline uploads to Google Drive;
                                     desktop app saves locally
```

Plus an optional side-input:

```
local_sources.json
         │
         ▼
  load_local_markdown_items()        local_markdown_source.py — read dated markdown files
         │                           you already maintain; no re-summarization needed
         └─► merged into fetch_all_sources() results before formatting
```

### Dev mode vs. frozen mode

| Mode | How it runs | Config reads from | Data writes to |
|------|------------|-------------------|----------------|
| **Dev** | `Launch Audio Briefing.command` or `python3 gui_app.py` | Script directory (`daily_audio_briefing/`) | Script directory |
| **Frozen** | Built `.app` bundle (PyInstaller) | `sys._MEIPASS` (bundled assets) | `~/Library/Application Support/Daily Audio Briefing/` |

**Config load order** (consistently applied throughout the codebase):

1. Explicit `data_dir` override (server / daemon mode)
2. macOS App Support directory
3. Script directory (dev mode)

When a config file exists in multiple locations, the earlier entry in that chain wins.

---

## The extension seams

### Source types

Sources are typed as `SourceType.YOUTUBE`, `SourceType.RSS`, or `SourceType.ARTICLE_ARCHIVE`
(the `newsletter` type in `sources.json` maps to `ARTICLE_ARCHIVE`). The enum is defined in
`source_fetcher.py`.

Routing:
- `source_processor.py` → `process_sources()` handles the legacy `channels.txt` code path
- `source_fetcher.py` → `load_sources()` parses `sources.json` into `SourceConfig` objects;
  `SourceFetcher.fetch_all_sources()` dispatches each one based on `source_type`

To add a new source type:
1. Add a variant to `SourceType` in `source_fetcher.py`
2. Add a detection heuristic in `_infer_type()`
3. Add a `_fetch_<type>()` method on `SourceFetcher`
4. Dispatch it in `fetch_all_sources()`

### The two summarizer prompt paths — keep them in sync

The summarizer runs in two distinct code paths. If you change a filter rule in one, you must
change it in the other, or the scheduled briefing and the manual "Get Summaries" button will
behave differently:

| Path | Entry point | Used when |
|------|------------|-----------|
| **Scheduled** | `scheduler._execute_pipeline_task()` → `SourceFetcher._summarize_youtube()` | Automated daily run |
| **Manual** | `get_youtube_news.summarize_text()` | "Get Summaries" button in the desktop app |

Both functions call into `llm_fallback.py`, but they construct the prompt independently. Edit
both or neither.

### The `custom_instructions` filter contract

`custom_instructions.txt` is loaded at runtime and passed to `SourceFetcher.fetch_all_sources()`
as `youtube_instructions` and `article_instructions`. The scheduler loads it via this search
order:

1. `data_dir` (daemon/server override)
2. macOS App Support directory
3. Script directory

The instructions are treated as **mandatory** by both prompt paths — they override the default
"be comprehensive" directive. An empty or missing `custom_instructions.txt` means no filtering
at all, which allows ads, promos, and off-topic segments through. If you maintain two copies
(one in the script dir for dev, one in App Support for the frozen app), keep them identical.

### The free LLM fallback chain (`llm_fallback.py`)

The chain is defined in `_HTTP_PROVIDERS` (a list of dicts, tried in order):

```
cerebras → cloudflare → groq → sambanova → mistral → ollama_cloud → openrouter
```

Each entry has a `key_env` (the environment variable name), a `ceiling` (max tokens that
provider handles cleanly), and provider-specific URL/model config. The chain skips any
provider whose `key_env` is not set.

**To reorder or disable a provider:** move or remove its entry in `_HTTP_PROVIDERS`.

**To add a provider:** add a new dict following the same shape. At minimum you need `name`,
`key_env`, `ceiling`, `base_url`, and `model`.

**Gemini** is gated by `ENABLE_GEMINI=1` (default off — zero-spend is the default). Set it in
`.env` if you want Gemini as part of the chain.

**Local Ollama fallback:** `ENABLE_LOCAL_FALLBACK=1` (default on) adds a local Ollama model
(`LOCAL_LLM_MODEL`, default `gpt-oss:20b`) as the final fallback. Configure `OLLAMA_HOST` if
Ollama is not on `localhost:11434`.

### The local-markdown reuse adapter (`local_markdown_source.py`)

Entry point: `load_local_markdown_items(data_dir, config=None)`

This adapter lets you include markdown files you already maintain (a notes folder, a personal
wiki, a journal) as briefing segments, without fetching or re-summarizing them. The app reads
them, applies a recency filter, and merges them into the briefing alongside fetched sources.

The adapter is **off by default** — it's a no-op when `local_sources.json` doesn't exist or
when no folders have `"enabled": true`.

**Config file:** `local_sources.json` (copy from `local_sources.example.json`)

**Full schema:**

```json
{
  "base_dir": "~/notes",
  "lookback_days": 10,
  "folders": [
    {
      "subdir": "newsletters/the-batch",
      "source_name": "The Batch",
      "enabled": true,
      "date_keys": ["date_published", "date_added", "date"],
      "date_from_filename": true,
      "exclude_filename_contains": ["Log", "Index"],
      "min_chars": 80
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `base_dir` | string | Root directory containing your notes. `~` is expanded. Also overridable via `LOCAL_MARKDOWN_DIR` env var (legacy alias: `PONTUS_VAULT_DIR`). |
| `lookback_days` | int | How many calendar days back to search for dated notes (default: 10). |
| `folders[].subdir` | string | Path relative to `base_dir` to scan. |
| `folders[].source_name` | string | Display label used in the briefing narration. |
| `folders[].enabled` | bool | Set `false` to skip this folder without removing the entry. |
| `folders[].date_keys` | list of strings | Frontmatter YAML keys to try for the note's date (tried in order). |
| `folders[].date_from_filename` | bool | If `true`, also try to parse a `YYYY-MM-DD` date from the filename (tried after frontmatter). |
| `folders[].exclude_filename_contains` | list of strings | Skip files whose name contains any of these substrings (case-sensitive). |
| `folders[].min_chars` | int | Minimum character count; files shorter than this are skipped. |

**Worked example:** suppose you keep dated summaries in
`~/notes/newsletters/<name>/<name>-YYYY-MM-DD.md` with frontmatter like:

```yaml
---
date_published: 2026-06-25
---
```

and each file starts with a one-line blockquote summary. Your config would be:

```json
{
  "base_dir": "~/notes",
  "lookback_days": 7,
  "folders": [
    {
      "subdir": "newsletters/weekly-digest",
      "source_name": "Weekly Digest",
      "enabled": true,
      "date_keys": ["date_published", "date"],
      "date_from_filename": true,
      "exclude_filename_contains": ["_index", "_template"],
      "min_chars": 100
    }
  ]
}
```

Files from the past 7 days are picked up, template and index files are skipped, and the
content appears in your briefing under the label "Weekly Digest".

---

## Config and data-dir model

Every config file has an `.example.*` counterpart that ships in the repo. Real files
are gitignored to keep personal data out of version history.

| Example file | Copy to | What it controls |
|-------------|---------|------------------|
| `.env.example` | `.env` | API keys and feature flags |
| `sources.example.json` | `sources.json` | Sources to fetch and summarize |
| `custom_instructions.example.txt` | `custom_instructions.txt` | Mandatory summarizer filter |
| `local_sources.example.json` | `local_sources.json` | Optional local-markdown reuse |
| `channels.example.txt` | `channels.txt` | Legacy YouTube-only source list |
| `instruction_profiles.example.json` | `instruction_profiles.json` | Named filter profiles |

The real files are gitignored because they often contain:
- API keys (`.env`)
- Personal channel lists that could identify you (`sources.json`, `channels.txt`)
- Personal interests and filter rules (`custom_instructions.txt`)
- Paths to your local notes directory (`local_sources.json`)

---

## Customizing with an AI assistant

Point your assistant at these files as context before asking it to modify behavior:

| File | Why |
|------|-----|
| `CLAUDE.md` | Project map, architecture facts, and conventions |
| `source_fetcher.py` | Source types, fetch dispatch, summarizer prompt |
| `scheduler.py` | Pipeline task execution, custom_instructions loading |
| `local_markdown_source.py` | Local-markdown adapter schema and parsing |
| `llm_fallback.py` | Provider chain, Gemini/local flags |

**Example asks:**

- *"Add a Mastodon source type that fetches a user's public timeline as an RSS feed and
  slots it into SourceType alongside youtube/rss/newsletter."*
  → The assistant needs `source_fetcher.py` (SourceType enum, fetch dispatch, `_infer_type`)
  and `source_processor.py` (detect_source_type).

- *"I keep dated summaries in `~/notes/newsletters/weekly-digest/`. Add a local_sources.json
  entry so the briefing reads from that folder for the past 5 days."*
  → The assistant needs `local_markdown_source.py` (schema) and `local_sources.example.json`
  (format reference). No code changes needed — just a config edit.

---

## Testing your changes

Run the test suite:

```bash
python3 -m pytest daily_audio_briefing/tests/ -v
```

**Before pushing, always keep this test green:**

```bash
python3 -m pytest daily_audio_briefing/tests/test_public_repo_privacy.py -q
```

`test_public_repo_privacy.py` scans the tracked files for patterns that would leak personal
data (real home paths, email addresses, personal system names) into the public repo. It must
pass before any push.
