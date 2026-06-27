# Customizing Your Audio Briefing

This guide walks you through setting up a personalized daily audio briefing — step by step,
no prior coding experience needed.

The app ships with **example** config files. The workflow is always the same: copy each
`*.example.*` file to its real name and edit it. Your real config files are listed in
`.gitignore`, so they stay private even if you share or fork the repo.

---

## Prerequisites

- **Python 3.12 or newer** — check with `python3 --version`
- **Dependencies:**
  ```bash
  pip install -r daily_audio_briefing/requirements-desktop.txt
  ```

---

## Step 1 — Add an AI provider key

Copy the example environment file:

```bash
cp daily_audio_briefing/.env.example daily_audio_briefing/.env
```

Open `daily_audio_briefing/.env` in any text editor. You only need **one** free API key to get
started. The app tries providers in priority order and automatically falls back if one is busy.

**Easiest options (free, no credit card):**

| Provider | Sign-up URL | Key variable |
|----------|-------------|--------------|
| Cerebras | https://cloud.cerebras.ai/ | `CEREBRAS_API_KEY` |
| Groq | https://console.groq.com/keys | `GROQ_API_KEY` |

Paste your key next to the matching variable, for example:

```
CEREBRAS_API_KEY=your-key-here
```

**Google Gemini** is optional and off by default (`ENABLE_GEMINI=0`). Leave it disabled unless
you specifically want to use Gemini and are comfortable with potential API costs.

Adding more keys (from different providers) gives the app extra fallback options when free-tier
rate limits are hit — but a single key is enough to run.

---

## Step 2 — Choose your sources

Copy the example sources file:

```bash
cp daily_audio_briefing/sources.example.json daily_audio_briefing/sources.json
```

Open `sources.json`. It's a list where each entry has three required fields:

```json
{
  "url": "https://...",
  "enabled": true,
  "type": "youtube"
}
```

**Source types:**

- `"type": "youtube"` — a YouTube channel (use the channel `/videos` URL)
- `"type": "rss"` — any RSS/Atom feed URL
- `"type": "newsletter"` — a newsletter archive page (e.g. on Beehiiv or Substack)

Set `"enabled": false` on any entry you want to temporarily skip without deleting it.

> **Note:** `channels.txt` (one YouTube URL per line) still works as a legacy fallback if
> you prefer a plain-text list.

---

## Step 3 — Tell it what to keep and what to drop

This is the most important customization. The summarizer reads your instructions as a
**mandatory filter** that overrides everything else — it's how you block ads, promos,
and off-topic content.

Copy the example:

```bash
cp daily_audio_briefing/custom_instructions.example.txt daily_audio_briefing/custom_instructions.txt
```

Open `custom_instructions.txt`. The structure is:

```
Focus on:
- [What matters to you]

Omit entirely:
- [What to skip]
```

**Example edit** — if you follow technology and want to cut all sponsor segments:

```
I'm interested in technology, software, and startups.

Focus on:
- New tools, products, or research being released
- Concrete numbers, benchmarks, and specifics
- What changed and why it matters

Omit entirely:
- Sponsor reads, discount codes, and ads
- Invitations to join Discord, Patreon, or paid communities
- Intraday price predictions and trading signals
```

Be concrete. Vague instructions produce vague filters. The summarizer treats your text as
an obligation, not a suggestion.

---

## Step 4 — Pick a voice

The app offers two text-to-speech engines:

| Mode | Engine | Speed | Quality | Notes |
|------|--------|-------|---------|-------|
| **Fast** | gTTS | ~10–30 s | Good | Requires internet; uses Google TTS |
| **Quality** | Kokoro ONNX | ~1–5 min | Excellent | Runs locally; first run downloads the model |

Choose in the desktop app's Audio tab, or set `audio_quality` in a scheduled task (values:
`"fast"` or `"quality"`).

---

## Step 5 — Run it

**Desktop app:**
```bash
open "Launch Audio Briefing.command"
```

Or double-click `Launch Audio Briefing.command` in Finder.

Use the **Summarize** page to fetch and summarize your sources, then the **Audio** page to
generate the briefing MP3.

**Scheduling:**
The **Scheduler** page lets you set a daily time. The daemon runs in the background and
places output files in `Week_N_YYYY/` folders inside your data directory
(`~/Library/Application Support/Daily Audio Briefing/` on macOS).

---

## Optional — Reuse markdown you already maintain elsewhere

If you already keep dated summaries in a folder of markdown files (a notes app, a personal
wiki, a journal), the app can voice them directly as briefing segments — without re-fetching
or re-summarizing. This saves AI calls and avoids duplication.

Copy the example:

```bash
cp daily_audio_briefing/local_sources.example.json daily_audio_briefing/local_sources.json
```

Edit `local_sources.json` to point at your notes folder. See
[docs/POWER-USER-GUIDE.md](docs/POWER-USER-GUIDE.md) for the full field reference and a
worked example.

This feature is off by default — the file simply doesn't exist until you copy it.

---

## Troubleshooting

See the **Troubleshooting** section in [README.md](README.md) for common issues (missing
dependencies, API key errors, audio generation failures).
