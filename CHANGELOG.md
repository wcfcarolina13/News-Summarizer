# Changelog

All notable changes to the Daily Audio Briefing, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/). This is an alpha project
deployed from the working tree, so entries are dated rather than tied to release
tags.

## 2026-09-03

### Added
- **MCP server (`dab-mcp` / `mcp_server.py`)** — any MCP client (Claude Code, Claude Desktop, Cowork, Cursor) can call `text_to_audio` / `urls_to_audio`, poll `get_job`, and list voices, with the GUI closed. One-line setup via `--install`; `--print-config`, `--uninstall`, `--check` also provided. Jobs run on a single worker thread and persist as JSON under `<data dir>/jobs/`, so a restarted server still reports finished work.
- **`audio_jobs.py`** — the Reading List → Audio and Direct Audio pipeline (fetch → Gemini/fallback clean → combine → Kokoro/gTTS) as Tk-free functions with progress and cancel callbacks. Both GUI dialogs now call it; 364 net lines deleted from `gui_app.py` (450 removed, 86 added) across the two GUI rewires (`_clean_single_article`, `generate_audio_filename`, the inline frozen/dev TTS branch, `get_data_directory` moved to `file_manager`).
- Second PyInstaller executable `dab-mcp` inside the .app / beside the .exe (built 2026-09-03 and installed to /Applications; `dab-mcp --check` verified from inside the bundle).
- **Optional Drive upload of MCP renders** — `text_to_audio` / `urls_to_audio` gain `upload_to_drive` and `drive_folder`, mirroring the scheduler's `_pipeline_drive_upload` guard order (reauth → signed-in → per-file upload) to push the rendered MP3 + TXT into the app's Drive folder; a Drive failure is recorded on the job's `drive` field without failing the render itself.

### Security
- **SSRF guard on `urls_to_audio`.** URLs supplied by an agent are now resolved and rejected when any resulting address is loopback, private, link-local, reserved or multicast (and the literal host `localhost`), so the MCP server cannot be steered at cloud metadata endpoints or localhost-only services; redirects are no longer auto-followed — each `Location` hop (max 3) is re-validated against the same rule. Set `DAB_MCP_ALLOW_PRIVATE_URLS=1` to opt out when pointing it at a local dev server. The GUI path is unchanged (the user typed those URLs).

### Fixed
- **stdout corruption of the MCP stdio transport.** `llm_fallback._log` printed to stdout and debug logging defaulted ON, so any URL job with cleaning enabled wrote `[LLM Fallback] …` straight into the JSON-RPC stream. `build_server()` now sets `DEBUG_FALLBACK=0` and flips `llm_fallback.LOG_TO_STDOUT` to False, routing those messages through the `dab.llm_fallback` logger instead; GUI and daemon behaviour is unchanged.
- MCP job records store only `{url, title, error}` per article instead of the full `content`/`cleaned` bodies, which were rewritten on every progress tick and returned to the agent.
- `list_jobs` clamps `limit` to 1–200; `job_store` tolerates a stray non-job JSON file in the jobs directory.
- Reading List → Audio: a TTS timeout now reports a proper failure instead of a raw error; frozen builds run TTS from the data dir so Kokoro model downloads don't land in `Reading List/`.
- Starting a second MCP server process no longer marks a live sibling's running job as failed; recovery now checks the owning pid.

### Notes
- Reading List → Audio previously mapped the model combo-box label through a stale lookup table and always cleaned with `gemini-2.5-flash` regardless of selection; both the Reading List and Direct Audio paths now use the selected model id via `_selected_gemini_model()`.
- Follow-up filed in the vault: re-evaluate whether Gemini is still the right cleaning/summarizing model given the free-provider chain.

## 2026-08-03 (evening)

### Fixed
- **Briefings re-spoke RSS/article content already delivered.** The Aug 3 briefing was **54%
  verbatim-identical to Aug 2**: of its 4 items, 2 were repeats — and both were RSS items dated
  Aug 2. The YouTube items were correctly deduped (`Skipped by cache: 6` for `@UnchainedCrypto`
  in that run's log), which is what isolated the cause.
  - **Two things compounded.** `scheduler.py` computes `cutoff = datetime.now() - timedelta(hours=24)`,
    but the RSS filter compares `pub_date.date() < cutoff_date.date()` — truncated to **date**
    granularity, so a 24h window covers up to 48h and everything dated "yesterday" is in scope
    regardless of clock time. And RSS items had **no dedup cache at all**: videos had
    `processed_videos.json`, local notes had `voiced_newsletter_notes.json`, articles had nothing.
  - **Intermittent, which is why it went unnoticed.** Across the last 8 briefings only Jul 28 and
    Aug 3 show repeats, both RSS-only — and both follow an unusually *late* run the previous day
    (Jul 27 ran 08:37; Aug 2 was the 18:45 outage recovery). A late run sweeps up same-day items,
    which the next morning's run then re-reads. The Aug 2 recovery maximised the overlap, and with
    only 2 new videos available that morning the repeats went from background noise to half the
    briefing.
  - **Fix:** articles now get exactly the treatment videos already had. `video_cache.py` gains an
    `articles` bucket (same file, same 30-day TTL) keyed by a normalised URL — trailing slash and
    fragment stripped, query kept, since feeds vary those between runs. `_fetch_rss` checks it
    *before* summarizing, so a repeat costs no LLM call. Commit is deferred until the delivery
    verdict via `_pending_articles` / `commit_article_urls`, so a crashed or failed-upload run
    leaves articles eligible for retry — the June lesson, applied to the one source type still
    missing it.
  - **Deferred renders carry articles too.** `pending_render.json` now records `article_urls`
    alongside `video_ids`; without it a GPU-deferred render would deliver its articles and leave
    them uncached, reintroducing the same bug in the resume path.
  - **Hardened the manifest write.** It builds the sidecar inside a `try/except`, so an
    `AttributeError` on any one field silently discarded the *entire* manifest — video IDs
    included. Fields are now read via `getattr`, so a partial fetcher degrades one field instead of
    losing the lot. This surfaced when four existing `test_render_gate_wiring` tests failed against
    a stub fetcher; they pass unmodified against the hardened version.
  - Backward compatible: caches and manifests written by the previous build load fine (verified
    against the live 234-video cache). Verified end-to-end against the real Substack feeds —
    cold run returned 4 items including both articles that duplicated; the same window after a
    delivery commit returned 0.
  - Tests: `tests/test_rss_dedup.py`, `tests/test_render_manifest_articles.py`. 122 pass.

## 2026-08-03 (later)

### Fixed
- **Watchdog was blind to the GUI's run-now paths.** When the task watchdog landed, only the
  daemon's `_execute_task` was converted to `_mark_running`/`_unmark_running`; `backfill_task`,
  `reenrich_task` and `retitle_task` still mutated `_running_tasks` directly, so `_running_since`
  never got an entry and `overdue_tasks()` couldn't see a hang started from the desktop app. All six
  sites now go through the helpers. Guarded by `tests/test_running_state_invariant.py`, which
  asserts structurally that the helpers are the *only* mutators — the behavioural tests can't cover
  it, because those methods do real network work and aren't callable from a unit test.

### Added
- **yt-dlp channel-listing backend** (`fetch_channel_videos_ytdlp`), slotted between RSS and
  scrapetube. The chain is now `DEFAULT_BACKENDS = ("rss", "ytdlp", "scrapetube")` — RSS leads
  because it's cheapest when healthy (<1s), yt-dlp sits ahead of scrapetube because scrapetube is
  the one that hangs. Built because both existing backends failed simultaneously: scrapetube hangs
  YouTube-side, and the RSS feed dropped to ~5% success (failure runs of 5–10 consecutive requests)
  while yt-dlp kept working throughout.
  - **Dates are the whole difficulty.** yt-dlp's flat listing is cheap (~0.4s/15 videos) but carries
    no dates at all — `timestamp`, `upload_date` and `release_timestamp` are all None. A real date
    costs a per-video extract (~1s, measured). That expense is unavoidable, because
    `source_fetcher._fetch_youtube` filters with `if pub_date and pub_date.date() < cutoff_date...`
    — **guarded on `pub_date` being truthy, so an undated video is not filtered** and would be
    summarized however old it is. The backend therefore returns *only* dated videos and drops the
    rest.
  - Cost is bounded twice: `YTDLP_MAX_DATE_LOOKUPS` (8) caps lookups per channel, and the scan stops
    after `YTDLP_STOP_AFTER_OLD` (2) *consecutive* entries older than `YTDLP_MAX_AGE_DAYS` (21).
    Two consecutive rather than one, because channels pin videos — a pinned old video sits at
    position 0 and would otherwise end the scan immediately and return nothing for that channel.
  - `socket_timeout` is set explicitly. The whole incident began with an unbounded socket read.
  - Verified live: 8 dated videos per channel in ~9s across three channels, correct relative-date
    strings. Forced-outage end-to-end: RSS down → yt-dlp covers in ~9s; all three down → returns in
    exactly 25.0s (the scrapetube bound) with no hang.
- `PREFER_RSS` (added earlier the same day) is superseded by `DEFAULT_BACKENDS` and removed — one
  ordering knob rather than two, now that there are three backends. `fetch_channel_videos_with_fallback`
  takes a `backends` tuple; both production callers use the default.

## 2026-08-03

### Changed
- **RSS is now the primary YouTube backend; scrapetube is the fallback** (`PREFER_RSS`).
  scrapetube broke YouTube-side — it hangs on some channels and returns empty on others — so
  leading with it cost ~50s of dead wait per run (two 25s hangs before the circuit breaker opens)
  before reaching the path that actually worked. RSS answered in <1s for every channel tested.
  scrapetube stays as the fallback for channels RSS can't resolve, still timeout-bounded, so the
  hang guard protects it in either position. Flip `PREFER_RSS` to False if scrapetube recovers and
  the ~15-video RSS ceiling starts to bite (it only matters for deep backfills; a daily run is
  nowhere near it).
- **yt-dlp 2025.11.12 → 2026.7.4**, floor in `requirements-desktop.txt` raised from `>=2023.1.0`.
  The stale version 403'd on every subtitle download — 72 in the Aug 2 run alone. Videos without a
  transcript are dropped, so this had been silently shrinking the briefing. Verified after upgrade:
  5/5 subtitle downloads succeeded in ~1s each, zero 403s.

### Fixed
- **RSS feed fetch now retries transient failures** (`RSS_ATTEMPTS`, `RSS_RETRY_BACKOFF`). Promoting
  RSS to primary made its single-shot fetch the weak link. Confirmed non-authoritative failures:
  the *same valid* channel id returned HTTP 404 and then HTTP 200 with 15 entries seconds apart,
  with ids independently verified against yt-dlp's `channel_id` (so this is not the resolver
  picking a wrong id — it isn't). 404 is retried alongside 5xx for that reason.

### Known issue
- **YouTube's feed endpoint was severely degraded when this shipped** (2026-08-03 ~00:40 CST):
  measured 1/10 and 0/10 successful fetches across two channels, with failure runs of 5 and 10
  consecutive requests, identical across four User-Agents and stable over 60s+ — server-side, not
  rate-limiting (no 429) and not client-specific. The same endpoint was 100% reliable earlier the
  same day. `RSS_ATTEMPTS=3` covers brief flaps, not runs that long, so while this persists the
  YouTube portion of a briefing may come up empty (other sources are unaffected; the pipeline
  already tolerates 0-item sources). yt-dlp is currently the only YouTube path that works reliably
  — a yt-dlp-based channel-listing backend is the obvious next move if this doesn't recover.

## 2026-08-02

### Fixed
- **Daemon wedged for ~33h on a timeout-less YouTube read; three days of briefings lost
  (Jul 31 – Aug 2, last delivery `2026-07-30_News.txt`).** `youtube_rss.fetch_channel_videos_with_fallback`
  called `list(scrapetube.get_channel(...))` with no bound. scrapetube passes no `timeout=` to its
  requests session and nothing sets a global socket timeout, so a YouTube-side stall blocked in
  `recv()` **forever** — never returning, never raising, which made the surrounding `try/except`
  and the healthy RSS fallback beneath it both unreachable. Confirmed by stack sample: 2622/2622
  samples in `read()` under `SSL_read_ex` ← `_buffered_readline` ← `gen_iternext`/`list_extend`
  (scrapetube's paginating generator), process at 0% CPU holding an ESTABLISHED socket to a Google IP.
  - **Blast radius was everything, not just the briefing.** `_run_loop` executes tasks *inline*
    (`scheduler.py:606`), so the blocked read stopped the loop reaching its next iteration —
    CryptoSum and RWA died too. On-disk `last_run` froze at Jul 30 because `save_tasks()` is only
    called on completion paths. The separate 60s reload thread stayed alive, re-arming
    `next_run = now+10s` every minute with nothing left to consume it: ~3,600 lines of
    "missed today's run" spam and a 7.9 MB log.
  - **Fix 1 — bounded scrapetube.** It now runs on a throwaway daemon thread with a hard
    `SCRAPETUBE_TIMEOUT` (25s), then falls through to RSS. A blocked thread can't be killed from
    Python, so it is abandoned rather than joined. Plus a per-process circuit breaker
    (`SCRAPETUBE_FAILURE_LIMIT`, 2): when scrapetube breaks it breaks for every channel, and
    12 channels × 25s would add 5 minutes of dead wall-clock to every run.
  - **Fix 2 — task watchdog.** `Scheduler._running_since` records each task's start;
    `overdue_tasks()` reports overruns; `scheduler_daemon._start_task_watchdog` polls every 60s and,
    past `TASK_WATCHDOG_SECONDS` (3h, env-overridable), notifies and `os._exit(1)` so the
    LaunchAgent's `KeepAlive=true` restarts clean and catch-up resumes. `_mark_running`/`_unmark_running`
    keep the mutex and the start-time map from drifting.
  - **Fix 3 — the silence.** `_notify()` fires only from `on_task_complete`, which a hang never
    reaches (it neither returns nor raises). The watchdog is now the path that alerts. This was the
    second multi-day outage in two months found via an empty Drive folder rather than an alert.
  - Not a regression: no code changed since Jul 12 (before the daemon started), clean working tree,
    no dependency changes since December. scrapetube 2.6.0 broke YouTube-side — verified live, it
    hangs on `@WesRoth` and `@UnchainedCrypto` and returns empty for a third channel, while RSS
    returns 15 videos/channel in <1s.
  - Tests: `tests/test_youtube_fetch_timeout.py`, `tests/test_task_watchdog.py`. 85 pass.

## 2026-06-27

### Fixed
- **Reused local notes now read cleanly as audio.** Auditing a live briefing showed the
  local-markdown reuse path voiced notes verbatim, so the TTS read aloud "read-only" artifacts,
  a marketing footer, and dense statistics tables.
  - `local_markdown_source._clean_body` drops the trailing "Connection Points" cross-reference
    block, pipeline meta lines, citation/reference lines, and raw URLs/DOIs; `_clean_title` removes
    a duplicated leading source name (no more "From The Batch, The Batch —").
  - `format_items_for_audio` strips newsletter/subscribe footers ("Thanks for reading… Subscribe
    for free… support my work") from every summary before TTS — the Substack CTA that had leaked
    from an RSS feed. Patterns are anchored to specific footer shapes so editorial "subscribe" /
    "thanks for reading" sentences survive.
  - The scheduler re-voices each local note via `SourceFetcher.rewrite_local_note_for_audio`, which
    keeps the narrative but condenses dense statistic/benchmark/pricing runs into a spoken takeaway
    (a `length_rule` override on `_summarize_article`, reusing the reasoning-leak guard; the free
    fallback chain makes the extra pass ~free). Skipped in cooldown — deterministic cleaning still
    applies, and a failed/leaked rewrite falls back to the cleaned text (never truncated/blank).
  - Tests: artifact stripping + URL false-positive safety (`test_local_markdown_source.py`); footer
    removal + editorial false-positive safety (`test_marketing_strip.py`). 44 pass.

## 2026-06-26

Public-readiness & customization pass: make the app usable out-of-box and
customizable by others without leaking the owner's personal config from this
public repo.

### Added
- **Generic local-markdown reuse adapter** (`local_markdown_source.py`). The old
  `vault_newsletters.py` hardcoded one vault path + newsletter list; it is now
  config-driven via `local_sources.json` (copy `local_sources.example.json`):
  reuse *any* local markdown folder, off by default, no-op when unconfigured.
  `base_dir` resolves from env `LOCAL_MARKDOWN_DIR` → `PONTUS_VAULT_DIR`
  (back-compat) → config. Tests in `tests/test_local_markdown_source.py`.
- **Customization docs:** `CUSTOMIZING.md` (non-technical setup) and
  `docs/POWER-USER-GUIDE.md` (architecture, the extension seams, AI-assisted
  customization), linked from a new README "Customizing your briefing" section.
- **`.example` templates** for every personal config:
  `custom_instructions.example.txt`, `channels.example.txt`,
  `instruction_profiles.example.json`, `local_sources.example.json`.
- **Privacy-regression test** (`tests/test_public_repo_privacy.py`) — fails if
  personal config becomes tracked or owner PII appears in shippable code/config.

### Changed
- **`.env.example` rewritten** for the free multi-provider fallback chain —
  documents every provider key `llm_fallback.py` reads; you only need one; Gemini
  is optional and off by default (`ENABLE_GEMINI=0`).
- **Scheduler** no longer hardcodes `~/pontus/vault`; it calls the generic adapter.

### Security
- **Untracked personal config from the public repo** and gitignored it:
  `custom_instructions.txt`, `channels.txt`, `instruction_profiles.json`, plus
  runtime caches (`voiced_newsletter_notes.json`, `*.bak-*`) and internal planning
  docs (`docs/superpowers/`). Working copies stay on disk so the live daemon is
  unaffected. Going-forward removal — git history not rewritten.
- **Scrubbed maintainer home paths from public prose docs** (`CLAUDE.md`,
  `UX_FLOW_DIAGRAM.txt`, `CUSTOM_INSTRUCTIONS_GUIDE.md`) and removed the stale
  internal `docs/RECOVERY-HANDOFF.md`.

## [Unreleased] — 2026-06-08

### Fixed
- **Daemon log: collapse to a single writer.** `setup_logging` attached a
  `logging.FileHandler` on top of launchd's `StandardOutPath`/`StandardErrorPath`
  redirects — three independent file descriptions writing the same file. Every
  log record was written twice, and the racing offsets left NUL bytes that put
  `grep` into binary mode and silently hid matches during post-mortems. Now logs
  through a single `StreamHandler(sys.stdout)` and folds `stderr` into `stdout`
  (`os.dup2`), so the daemon's logging, its `print()`s, and child processes
  (yt-dlp, TTS) all share one description — no duplicate lines, no NUL gaps.
  Verified live: fds 1 and 2 resolve to the same inode/offset, and the startup
  banner now logs once instead of twice. (`scheduler_daemon.py`)

### Operational
- Restarted the scheduler LaunchAgent to activate `c94e388`. The daemon had run
  continuously since before that commit landed, so the briefing was still
  summarizing on Cloudflare's `@cf/nvidia/nemotron-3-120b-a12b` (leaked reasoning
  + looped on long inputs) whenever Cerebras returned 429 — the cause of recent
  briefings sounding "off." Now back on `@cf/openai/gpt-oss-120b`. No code change.

## 2026-06-05

### Added
- Full-body RSS summaries with per-segment channel attribution. (`c96c37f`)

### Fixed
- Cloudflare fallback pinned to `@cf/openai/gpt-oss-120b`; `nemotron-3-120b`
  leaked reasoning and looped on long inputs. (`c94e388`)

## 2026-06-03

### Added
- Stacked free OpenAI-compatible providers (Cerebras, Cloudflare, Groq,
  SambaNova, …) in the fallback chain — each an independent rate-limit pool, so
  the daily burst no longer 429-drops videos. (`4e50de1`)
- Free-LLM provider stress-test harness with `probe`/`burst`/`simulate` modes.
  (`9439ef8`)
- Per-provider models bumped to the validated-clean 120B tier. (`6fa53c5`)

### Fixed
- Corrected the Cerebras model id to `gpt-oss-120b` (the ported llama id 404'd).
  (`e2a34f7`)
- Block pure-TA channels and post-filter TA-dense summaries. (`363a5bf`)

### Security
- Prompt-injection guard on untrusted transcripts, hardened with per-call nonce
  delimiters and a red-team harness. (`8d233f3`, `eb24100`)

## 2026-05-29

### Added
- Local Ollama fallback tier plus Groq 429 retry; token-aware routing to keep
  oversized requests off low-ceiling providers. (`310d7fa`, `082f678`)

### Fixed
- Apply user content filters; block promos, intraday TA, and the RealVision /
  Raoul Pal Sui-promo segments. (`7ee7dbc`)

## 2026-05-26

### Fixed
- Honour `cooldown_enabled` in the outer pre-flight skip. (`20f2ae0`)

## 2026-05-13

### Changed
- Zero-spend budget semantics: route every Gemini call site through the free
  fallback chain. (`510cff1`)
