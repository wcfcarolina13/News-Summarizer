# Changelog

All notable changes to the Daily Audio Briefing, newest first. Format follows
[Keep a Changelog](https://keepachangelog.com/). This is an alpha project
deployed from the working tree, so entries are dated rather than tied to release
tags.

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
