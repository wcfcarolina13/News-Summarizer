# LLM call inventory — Daily Audio Briefing

Written 2026-09-03 for the "is Gemini still the right model?" review. Every
place the app asks a language model for text, what it needs, how big the
input is, how often it runs, and what actually answered it in the last month.

All call sites go through one function, `llm_fallback.generate_with_fallback`,
which tries Gemini (only if `ENABLE_GEMINI=1`), then the free providers in
order, then local Ollama. So "which model" is a property of the chain, not of
the call site.

## Call sites

| # | Call site (`caller` string) | What it does | Runs from | Input size | Output | Structured output? | Daily volume |
|---|---|---|---|---|---|---|---|
| 1 | `fetcher._summarize_yt` (`source_fetcher.py`) | Summarize one YouTube transcript for the audio briefing, applying `custom_instructions.txt` (omit rules). Nonce-delimited, injection-hardened prompt. | Scheduler daemon (07:00 briefing), GUI Summarize page | transcript capped at 50k chars (~12k tokens); median 17k chars, max 53k (Apr–May Gemini log) | 1–4k chars of TTS prose | No — plain prose | 3–18 videos/day (last 10 briefings: 7, 12, 12, 16, 8, 3, 10, 5, 10, 18 items incl. articles) |
| 2 | `fetcher._summarize_article` (`source_fetcher.py`) | Summarize an RSS/newsletter article for the briefing; bodies over 50k chars are map-reduced (`text_chunks.split_text`). Also re-voices local markdown notes. | Scheduler daemon, GUI | usually 3–20k chars; sections of 50k for long roundups | 2–4 paragraphs of prose | No | ~1–3/day (21 Cloudflare successes since Aug 12) |
| 3 | `audio_jobs.clean_text` (`audio_jobs.py`) | Clean a pasted text or fetched article for listening (strip nav, ads, captions; expand abbreviations). **Now chunked at ~6k tokens** with `max_tokens` sized to the chunk. | MCP server (`urls_to_audio`, `text_to_audio`), GUI Reading List / Direct Audio | anything — the Sep 3 MCP job had inputs of 5k, 11k, 14k, 19k, 21k, 22k, 40k tokens | roughly the same length as the input | No | bursty — 0 most days, ~20 calls when Bradley queues a reading list |
| 4 | `yt_news.summarize` (`get_youtube_news.py`) | Legacy script-mode YouTube summarizer (same rules as #1, kept in sync by hand). | `get_youtube_news.py` run via GUI "run script" only | ≤50k chars | prose | No | 0 in the daemon log — legacy path |
| 5 | `gui._summarize_yt`, `gui._clean_article` (`gui_app.py`) | GUI-only variants: transcript capped at 15k chars, article at 20k. | GUI Summarize page | ≤15k / ≤20k chars | prose | No | interactive only |
| 6 | `grid.analyze_profile` (`grid_api.py`) | Suggest a Grid profile update from a news item — returns `[TYPE]: suggestion` or "No updates needed". | Extraction tasks with Grid enrichment on | profile context + article, a few k chars | one line | Light — a tagged line, parsed by prefix | 0 in the daemon log and `fetch_debug.log` since Aug 12 (enrichment not active) |

The three extraction tasks (CryptoSum, ExecSum, data CSV) that run daily do not
call an LLM at all — they are regex/HTML extraction to Sheets.

### Gemini spend history (`api_usage.json`)

The tracker only records paid Gemini calls. The repo copy holds 500 calls,
all `fetcher._summarize_yt`, 2026-04-05 → 2026-05-24: 12.8 calls/day, median
input 17,196 chars, median output 3,525 chars, `gemini-2.5-flash`. Since
2026-06-10 every day is logged as "no paid calls — pipeline ran on free
chain". `ENABLE_GEMINI` is unset in `.env`, so Gemini has not been called by
the pipeline for three months; the answer to "is Gemini still the right
model" starts from the fact that it is not the model at all today.

## What actually answered, 2026-08-12 → 2026-09-03 (daemon log)

| Outcome | Count |
|---|---|
| Gemini skipped (`ENABLE_GEMINI` unset) | 229 |
| Cerebras HTTP 402 (dead hop, every call since Aug 18) | 189 |
| Cloudflare `@cf/openai/gpt-oss-120b` succeeded | 176 (155 videos + 21 articles) |
| Cerebras succeeded (before Aug 18) | 25 |
| Groq succeeded | 3 |
| Groq skipped by the 10k-token ceiling | 7 |
| Groq HTTP 429 / 413 | 8 / 7 |
| Cloudflare HTTP 429 ("used up your daily free allocation of 10,000 neurons") | 14 |
| **Items dropped — all providers failed** | **12 videos** (Cloudflare quota out, Groq 429, local Ollama not running) |

So for a month the briefing has effectively been a single-provider pipeline
on Cloudflare's gpt-oss-120b, with Groq taking the occasional small one and a
dead Cerebras call in front of every request.

Keys present in `.env`: Groq, Cloudflare, Cerebras, Gemini. **Mistral, Ollama
Cloud and OpenRouter have no key** — the Follow-Ups note's assumption that long
articles "fall to Mistral/Ollama Cloud/OpenRouter" was wrong; they fall to the
local 20B model, or fail.

## Live provider results, 2026-09-03 (`stress_test_providers.py probe`)

Cerebras verified first: `/v1/models` answers (`gpt-oss-120b`, `gemma-4-31b`)
but `/v1/chat/completions` returns `402 payment_required, param=quota`. The
key is valid; the free quota is gone. Removed from the chain.

| Provider | 6k-token prompt, 6k max_tokens | 9k-token prompt, 400 max_tokens | Rate-limit headers |
|---|---|---|---|
| groq `openai/gpt-oss-120b` | 200, 1.14 s, 1,230 chars | 200, 1.34 s, 914 chars | 1,000 req/day, **8,000 tokens/min** |
| cloudflare `@cf/openai/gpt-oss-120b` | 429 daily allocation used up | 429 | 10,000 neurons/day (exhausted by the morning MCP job) |
| local ollama `gpt-oss:20b-tuned` | 200, 32.9 s | 200, 15.5 s | none |
| openrouter / mistral / ollama_cloud | skipped — no key | | |

Reading: Groq is the fast rung and takes a 6k-token chunk with a 6k output
budget in about a second, which is why cleaning is now chunked at that size.
Cloudflare's 10k-neuron day is the binding limit for long inputs; once a big
reading-list job burns it, the rest of the day falls to the local floor (or
drops, if Ollama is not running). Adding one of the keyless providers
(OpenRouter free models is the obvious one — it also carries the Nemotron 3
Super free slot) would give long inputs a second pool.

## Candidate shortlist per call site (2026-09-03)

Sources: the `free-llm-fallback-chain` skill catalog, the FreeLLM API
Aggregator audit (vault, 2026-09-03), the Nemotron 3 Super assessment (vault,
2026-09-03), and the live probe above.

| Call site | Candidates, best first | Why |
|---|---|---|
| Briefing summarizer (#1, #2) | **Groq `openai/gpt-oss-120b`** (in use, fastest, budget-robust, clean prose); Cloudflare `@cf/openai/gpt-oss-120b` (same model, big requests); OpenRouter `nvidia/nemotron-3-super-120b-a12b:free` (262k ctx, needs an OpenRouter key + training opt-out; reasoning-mode output is verbose, must pass the reasoning-leak guard); Mistral `mistral-medium-latest` (needs key + opt-out); Gemini 2.5 Flash (paid, ~$0.005/video, the historical baseline) | gpt-oss-120b already produces the daily briefing and the reasoning-leak guard was built around it. Kimi-k2.6 on Cloudflare is **not** a candidate for TTS prose: it spends its budget on the reasoning channel and returns empty content at normal `max_tokens` (skill field notes 2026-07-04). |
| Cleaning (#3) | Groq gpt-oss-120b in ~6k-token chunks (now the default path); Cloudflare gpt-oss-120b for the rest; local floor | Output ≈ input length, so the model matters less than the token budget; chunking fixed the actual failure. |
| Grid suggestion (#6) | Groq gpt-oss-120b; Cloudflare | One-line tagged output, tiny input — any rung works. Not active. |

## Decision framing

The A/B switch (`DAB_SUMMARIZER=<provider>:<model>` in `.env`) tries one
provider first at the summarizer call sites only, then falls back to the
normal chain. `scripts/ab_summarize.py` runs Gemini and a candidate on the
same day's transcripts with the same prompt and writes `docs/ab/<date>_*.md`
for a listening comparison. The default is unchanged until Bradley decides.

## New free options processed through Pontus since mid-August (checked 2026-09-03)

Sources: vault notes modified since 2026-08-15, the processing log, and live
model lists from Groq and Cloudflare with the briefing keys.

| Option | Where it came from | Fit for the briefing | Verdict |
|---|---|---|---|
| **Groq `qwen/qwen3.8-27b`** (also `qwen3.6-27b`) — new on Groq's menu | live `/v1/models` | Tested $0 on a 6k-char prose rewrite: 2.8 s, clean (no markdown, no reasoning channel) but left 14 digits vs 0 for gpt-oss-120b. Same 8k tokens/min pool as gpt-oss, so it adds no capacity. | Not a chain change. Valid free B-side for `scripts/ab_summarize.py --b groq:qwen/qwen3.8-27b`. |
| **Cloudflare `@cf/zai-org/glm-5.3` / `glm-5.3-flash`**, `deepseek-v4-flash-0731`, `gemma-4-26b-a4b-it`, `qwen3.8-27b`, `kimi-k2.7-code` — new on the Workers AI catalog | live model search; GLM-5.3 weights noted in [[Wissner-Gross Smoothing the Singularity 2026-08-29]] | Same 10k-neuron/day pool as gpt-oss-120b, so no extra capacity; GLM/Kimi are reasoning models that spend the budget on the reasoning channel (skill field notes 2026-07-04). Untested today — Cloudflare's free day was already spent. | Candidates for a free-vs-free A/B on a fresh day (`--b cloudflare:@cf/zai-org/glm-5.3-flash`). Not a default change. |
| **OpenRouter `nvidia/nemotron-3-super-120b-a12b:free`** | [[Nemotron 3 Super]] (2026-09-03) | 262k context, free; needs an OpenRouter key + training opt-out; reasoning-verbose. | The one option that adds a **new pool** for long inputs. Worth a key. |
| GLM-5.2 on Cloudflare + Cohere `north-mini-code:free` on OpenRouter | [[Free Coding Models via Cloudflare Workers AI and OpenRouter]] | Already evaluated and wired into Hermes (Jul 4); coding-oriented, reasoning-hungry. | No. |
| FreeToken (local MoE inference engine) | [[FreeToken - Frontier MoE Models on Consumer GPUs]] | CUDA-only benchmarks; nothing for Apple Silicon. | No. |
| Qwen3.8-27B MLX build | [[Qwen3.8-27B-Uncensored MLX Build]] | ~13.5 GB at 4-bit, fits the M2 Pro; could replace `gpt-oss:20b-tuned` as the local floor if it proves faster/cleaner. | Maybe, as a local-floor experiment; not a hosted rung. |
| VibeVoice (Microsoft TTS/ASR) | [[GitHub Repos Evaluation 2026-09-03]] | TTS side, not LLM; research-only licence. | Out of scope here. |
| FreeLLM API Aggregator's long tail (GitHub Models, Pollinations, LLM7, OVH, AI Horde, HF Router…) | [[FreeLLM API Aggregator]] audit | GitHub Models is "caution" (evaluation-only ToS); the rest are unaudited. | Run the skill's 7-question audit before adding any. |

Net: nothing new displaces gpt-oss-120b on Groq/Cloudflare. The only change
that adds real capacity is an OpenRouter key (Nemotron 3 Super free slot),
which is a Bradley action (sign up, toggle the training opt-out, add the key).
