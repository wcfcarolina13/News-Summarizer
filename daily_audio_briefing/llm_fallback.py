"""
LLM Fallback Chain — Gemini → stacked free providers → local Ollama.

Provides a single generate_with_fallback() that tries providers in order, first
success wins. Gemini is first (off by default under the zero-spend budget), then
each configured free OpenAI-compatible provider in ``_HTTP_PROVIDERS`` (Groq,
Cloudflare, Mistral, Ollama Cloud, OpenRouter — enable one by
adding its key to .env), then local Ollama (gpt-oss:20b-tuned) as the always-
available, no-rate-limit floor. Stacking independent free tiers stops the daily
burst from 429-dropping videos on any single provider's tokens/min cap.

Override any provider model via the matching *_MODEL env var; local tier via
ENABLE_LOCAL_FALLBACK, OLLAMA_HOST, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT.

A/B switch for the briefing summarizer: set DAB_SUMMARIZER="<provider>:<model>"
(e.g. "groq:openai/gpt-oss-120b" or "openrouter:nvidia/nemotron-3-super-120b-a12b:free")
and the summarizer call sites (``_SUMMARIZER_CALLERS``) try that provider+model
FIRST, before Gemini and the normal chain. Unset (the default) changes nothing.

If all providers fail, ``generate_with_fallback`` returns None so the caller can
skip the item. The previous "extractive" fallback (first-25-sentences of the raw
transcript) was removed because it silently emitted unsummarized, disfluency-
laden transcript text into the audio brief. Set ALLOW_EXTRACTIVE=1 to opt back in.
"""

import logging
import os
import re
from typing import Optional

# Default to ON — fall-through events are rare and important. Set
# DEBUG_FALLBACK=0 in the environment to silence them.
_debug = os.environ.get("DEBUG_FALLBACK", "1").lower() in ("1", "true", "yes")
_allow_extractive = os.environ.get("ALLOW_EXTRACTIVE", "").lower() in ("1", "true", "yes")

# When False, _log routes through the logging module instead of print(). The MCP
# stdio server sets this False in build_server() because stdout IS its transport
# and a stray print corrupts the JSON-RPC stream. GUI/daemon keep the default.
LOG_TO_STDOUT = True

_logger = logging.getLogger("dab.llm_fallback")


def _log(msg: str):
    if _debug:
        # Print to stdout (captured by the scheduler/web log) AND tee into
        # fetch_debug.log so post-mortems can see why a brief came up empty.
        if LOG_TO_STDOUT:
            print(f"[LLM Fallback] {msg}")
        else:
            _logger.info("%s", msg)
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, "fetch_debug.log"), "a") as f:
                f.write(f"[LLM Fallback] {msg}\n")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Stacked free OpenAI-compatible providers.
#
# Each entry is an independent free tier; stacking them spreads the daily
# briefing burst across separate rate-limit pools so no single provider's
# tokens/minute cap silently drops a video. All are security-audited (2026-06-03)
# as safe for this zero-spend automated use: they don't train on free-tier API
# data (Groq, Cloudflare, Ollama Cloud), or training is
# user-disabled (Mistral, OpenRouter). SambaNova was removed 2026-09-03: its
# free tier was retired in June 2026 (402 after trial), so it only cost a dead hop.
# Cerebras was removed the same day for the same reason: every chat completion
# has returned HTTP 402 "payment_required" (param "quota") since 2026-08-18,
# while /v1/models still answers — the key is fine, the free quota is gone.
# Add a key to .env to enable a provider;
# providers without a key are skipped silently.
#
# Ordered by priority — highest sustained throughput first. `ceiling` is the
# per-request token cap above which a provider would 429 on its per-minute
# limit regardless of pacing, so we skip it for oversized requests. Groq leads
# (fastest rung; its 10k ceiling routes big requests straight past it), so
# Cloudflare's 10,000-neuron/day free allocation is spent only on the requests
# that Groq cannot take.
# Override any model via the matching *_MODEL env var.
# ---------------------------------------------------------------------------
import json as _json
import urllib.request as _urlreq
import urllib.error as _urlerr

_HTTP_PROVIDERS = [
    {"name": "groq",         "key_env": "GROQ_API_KEY",       "ceiling": 10000,
     "base": "https://api.groq.com/openai/v1",
     "model_env": "GROQ_MODEL",         "model": "openai/gpt-oss-120b"},
    {"name": "cloudflare",   "key_env": "CF_API_TOKEN",       "ceiling": 60000,
     "base": "https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1",
     "model_env": "CF_MODEL",           "model": "@cf/openai/gpt-oss-120b"},  # matches Groq; nemotron-3-120b leaked reasoning + looped on long inputs
    {"name": "mistral",      "key_env": "MISTRAL_API_KEY",    "ceiling": 30000,
     "base": "https://api.mistral.ai/v1",
     "model_env": "MISTRAL_MODEL",      "model": "mistral-medium-latest"},
    {"name": "ollama_cloud", "key_env": "OLLAMA_API_KEY",     "ceiling": 60000,
     "base": "https://ollama.com/v1",
     "model_env": "OLLAMA_CLOUD_MODEL", "model": "gpt-oss:120b"},
    {"name": "openrouter",   "key_env": "OPENROUTER_API_KEY", "ceiling": 30000,
     "base": "https://openrouter.ai/api/v1",
     "model_env": "OPENROUTER_MODEL",   "model": "google/gemma-4-26b-a4b-it:free",  # llama-3.3-70b:free retired (404 "unavailable for free", 2026-09-03); gemma-4 is the clean non-reasoning free prose model
     # OpenRouter free slots are shared upstream pools that go "temporarily rate-limited"
     # for minutes at a time, so ask OpenRouter to route to the next free model in ONE
     # request ("models" array) instead of burning the whole rung on a 429.
     # minimax-m3: clean spoken prose on the real briefing prompt (2026-09-03 A/B), no reasoning
     # channel, 5-7 s; gemma-4-31b dropped (429 upstream on every attempt that day).
     "fallback_models": ["minimax/minimax-m3:free", "nvidia/nemotron-3-super-120b-a12b:free"]},
]


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — good enough for routing."""
    return len(text) // 4


def _load_key(env_name: str) -> Optional[str]:
    """Return a key from the environment, falling back to the script-dir .env."""
    val = os.environ.get(env_name)
    if val:
        return val
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{env_name}="):
                        return line.split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass
    return None


def _provider_base_url(p: dict) -> Optional[str]:
    """Resolve URL placeholders (e.g. Cloudflare's account id). None if unresolved."""
    base = p["base"]
    if "{CF_ACCOUNT_ID}" in base:
        acct = _load_key("CF_ACCOUNT_ID")
        if not acct:
            return None
        base = base.replace("{CF_ACCOUNT_ID}", acct)
    return base


def _looks_degenerate(text: str) -> bool:
    """True if output looks like a repetition loop — a known gpt-oss failure on
    some inputs where it enumerates the same phrase until it hits the token cap
    (e.g. 'Also avoid X thousand. Use X thousand.' forever). Cheap heuristics: a
    collapsed vocabulary over a long output, or one short phrase dominating."""
    words = text.split()
    n = len(words)
    if n < 200:
        return False
    if len(set(words)) / n < 0.18:
        return True
    from collections import Counter
    bigrams = Counter((words[i], words[i + 1]) for i in range(n - 1))
    return bool(bigrams) and bigrams.most_common(1)[0][1] >= max(15, n // 40)


def _http_provider_generate(p: dict, prompt: str, max_tokens: int = 4096,
                            timeout: int = 120, model: Optional[str] = None) -> Optional[str]:
    """Call one OpenAI-compatible provider. None on any failure (caller moves on).

    A real User-Agent is required — several of these APIs are Cloudflare-fronted
    and 403 (error 1010) a bare urllib UA. On 429 we return None immediately so
    the chain falls through to the next provider's independent pool rather than
    sleeping; local Ollama is the floor under all of them.
    """
    key = _load_key(p["key_env"])
    if not key:
        return None
    base = _provider_base_url(p)
    if not base:
        _log(f"{p['name']} skipped: unresolved URL (missing CF_ACCOUNT_ID?)")
        return None
    model = model or os.environ.get(p.get("model_env", "")) or p["model"]
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    if p.get("fallback_models"):
        # OpenRouter routing: try these in order server-side if `model` is down/429.
        body["models"] = [model] + [m for m in p["fallback_models"] if m != model]
    payload = _json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "daily-audio-briefing/1.0",
        "Authorization": f"Bearer {key}",
    }
    req = _urlreq.Request(base + "/chat/completions", data=payload, headers=headers)
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            data = _json.loads(resp.read())
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        # Use ONLY the final answer channel. A reasoning model (gpt-oss) that
        # loops or exhausts its budget leaves content empty and fills the
        # reasoning channel with its chain-of-thought; returning THAT as the
        # summary leaks the model's internal monologue into the briefing (it got
        # read aloud once). Empty final content => this provider failed; fall
        # through to the next one rather than handing back raw reasoning.
        text = (msg.get("content") or "").strip()
        if not text:
            had_reasoning = bool(msg.get("reasoning") or msg.get("reasoning_content"))
            why = "reasoning-only, no final answer" if had_reasoning else "empty response"
            _log(f"{p['name']} ({model}) returned {why} — skipping provider")
            return None
        if choice.get("finish_reason") == "length":
            # Truncated mid-thought at max_tokens — unreliable for TTS, and the
            # tell-tale of a runaway reasoning loop. Let the next provider try.
            _log(f"{p['name']} ({model}) truncated at max_tokens — skipping provider")
            return None
        if _looks_degenerate(text):
            _log(f"{p['name']} ({model}) degenerate/looping output — skipping provider")
            return None
        _log(f"{p['name']} ({model}) returned {len(text)} chars")
        return text
    except _urlerr.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:120]
        except Exception:
            pass
        _log(f"{p['name']} HTTP {e.code}: {body[:100]}")
        return None
    except Exception as e:
        _log(f"{p['name']} error: {type(e).__name__}: {e}")
        return None


# ---------------------------------------------------------------------------
# Local provider — Ollama (gpt-oss:20b-tuned by default). Zero cost, no rate
# limits, fully offline. Slower than Groq, so it sits below it in the chain as
# a safety net so a Groq throttle/outage never silently drops a video.
# ---------------------------------------------------------------------------
_LOCAL_ENABLED = os.environ.get("ENABLE_LOCAL_FALLBACK", "1").lower() in ("1", "true", "yes")

# Gemini is a PAID surface and is the only thing in this chain that can cost
# money. It is OFF by default — the chain starts at the stacked free providers
# and ends at the local Ollama floor, so the whole pipeline runs at zero spend.
# Passing a gemini_model is no longer enough to trigger a paid call; you must
# ALSO explicitly opt in with ENABLE_GEMINI=1. This makes zero-spend the default
# regardless of any budget value in .env / api_usage.json.
_GEMINI_ENABLED = os.environ.get("ENABLE_GEMINI", "0").lower() in ("1", "true", "yes")

# A/B switch for the briefing summarizer (see module docstring). Only the
# summarizer call sites honour it; cleaning / extraction keep the normal chain.
_SUMMARIZER_CALLERS = frozenset({
    "fetcher._summarize_yt", "fetcher._summarize_article",
    "yt_news.summarize", "gui._summarize_yt",
})


def _summarizer_override() -> Optional[tuple]:
    """Parse DAB_SUMMARIZER="<provider>:<model>" into (provider dict, model).

    Read at call time (not import time) so a test or the A/B script can flip it.
    Returns None when unset, malformed, or naming an unknown provider."""
    raw = (os.environ.get("DAB_SUMMARIZER") or _load_key("DAB_SUMMARIZER") or "").strip()
    if not raw or ":" not in raw:
        return None
    name, model = raw.split(":", 1)
    name, model = name.strip().lower(), model.strip()
    for p in _HTTP_PROVIDERS:
        if p["name"] == name and model:
            return p, model
    _log(f"DAB_SUMMARIZER={raw!r} ignored: unknown provider {name!r}")
    return None


_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
_LOCAL_MODEL = os.environ.get("LOCAL_LLM_MODEL", "gpt-oss:20b-tuned")
_LOCAL_TIMEOUT = int(os.environ.get("LOCAL_LLM_TIMEOUT", "300"))


def _ollama_generate(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """Call a local Ollama model. Returns None if Ollama is down or errors.

    Uses stdlib urllib (no extra dependency). Fails fast to None when Ollama
    isn't running rather than hanging the pipeline.
    """
    if not _LOCAL_ENABLED:
        return None

    import json
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": _LOCAL_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": max_tokens},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{_OLLAMA_HOST}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_LOCAL_TIMEOUT) as resp:
            data = json.loads(resp.read())
        text = (data.get("response") or "").strip()
        if text:
            _log(f"Local ({_LOCAL_MODEL}) returned {len(text)} chars")
            return text
        _log(f"Local ({_LOCAL_MODEL}) returned empty response")
        return None
    except urllib.error.URLError as e:
        _log(f"Local LLM unreachable ({_OLLAMA_HOST}): {e}. Is Ollama running?")
        return None
    except Exception as e:
        _log(f"Local LLM error: {e}")
        return None


# ---------------------------------------------------------------------------
# Extractive fallback — no AI, just transcript cleanup
# ---------------------------------------------------------------------------

def _extractive_summary(transcript: str, title: str = "", max_sentences: int = 25) -> str:
    """Create a basic summary by cleaning and truncating the transcript.

    Not great quality, but always works with zero cost.
    """
    # Clean up the text
    text = transcript.strip()

    # Remove common YouTube intro phrases
    intro_patterns = [
        r"^(hey (guys|everyone|folks))[,!.]?\s*",
        r"^(what'?s up (guys|everyone|folks))[,!.]?\s*",
        r"^(welcome back to)[^.]*[.!]\s*",
        r"^(in this video)[^.]*[.!]\s*",
        r"^(today we'?(re|ll))[^.]*[.!]\s*",
    ]
    for pat in intro_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Filter out very short sentences (likely fragments)
    sentences = [s for s in sentences if len(s) > 20]

    # Take first N sentences
    selected = sentences[:max_sentences]

    result = " ".join(selected)

    # Ensure it doesn't end mid-sentence
    if result and result[-1] not in ".!?":
        last_period = result.rfind(".")
        if last_period > len(result) // 2:
            result = result[:last_period + 1]

    if title:
        return f"{result}"

    return result


# ---------------------------------------------------------------------------
# Main fallback chain
# ---------------------------------------------------------------------------

def generate_with_fallback(
    prompt: str,
    gemini_model=None,
    caller: str = "unknown",
    timeout: int = 120,
    max_tokens: int = 4096,
) -> Optional[str]:
    """Try Gemini → stacked free providers → local Ollama; first success wins.

    If DAB_SUMMARIZER names a provider:model and ``caller`` is a summarizer call
    site, that provider is tried first (A/B switch; default off).

    Gemini is tried first when a model is provided and within budget (it's off
    by default under the zero-spend budget). Then each configured provider in
    ``_HTTP_PROVIDERS`` is tried in priority order, skipping any whose per-
    request token ceiling this request would blow. Local Ollama is the floor.
    Stacking independent free tiers stops the daily burst from 429-dropping
    videos on any single provider's tokens/min cap.

    Args:
        prompt: The full prompt including transcript.
        gemini_model: A google.generativeai model instance (or None to skip).
        caller: Caller identifier for tracking.
        timeout: Per-provider request timeout.
        max_tokens: Output cap for the HTTP providers and the local floor. Size it
            for the task — cleaning returns roughly its input length, so a long
            chunk needs more than the 4096 default or gpt-oss truncates.

    Returns:
        Generated text, or None if all providers fail.
    """
    gemini_failed_reason: Optional[str] = None

    # --- Attempt 0: the A/B summarizer override (DAB_SUMMARIZER) ---
    override = _summarizer_override() if caller in _SUMMARIZER_CALLERS else None
    if override:
        p, model = override
        if not _load_key(p["key_env"]):
            _log(f"DAB_SUMMARIZER wants {p['name']} but {p['key_env']} is not set — using normal chain")
        else:
            result = _http_provider_generate(p, prompt, max_tokens=max_tokens,
                                             timeout=timeout, model=model)
            if result:
                _log(f"{p['name']} ({model}) [DAB_SUMMARIZER] succeeded for {caller}")
                return result
            _log(f"DAB_SUMMARIZER {p['name']}:{model} failed for {caller} — falling back to normal chain")

    # --- Attempt 1: Gemini (PAID — opt-in only) ---
    # Skipped entirely unless ENABLE_GEMINI=1. This is the zero-spend default:
    # even when a gemini_model is handed in, we do not make a paid call. The
    # free stacked providers + local floor below cover summarization at $0.
    if gemini_model is not None and not _GEMINI_ENABLED:
        gemini_failed_reason = "skipped: Gemini disabled (set ENABLE_GEMINI=1 to allow paid calls)"
        _log(f"Gemini skipped for {caller}: ENABLE_GEMINI not set — going straight to free chain")
    elif gemini_model is not None:
        try:
            from api_usage_tracker import get_tracker, FreeTierExceeded, BudgetExceeded, APILimitExceeded
            response = get_tracker().tracked_generate(
                gemini_model, prompt, caller, timeout=timeout
            )
            text = response.text
            if text and text.strip():
                _log(f"Gemini succeeded ({len(text)} chars) for {caller}")
                return text
            gemini_failed_reason = "empty response"
        except (FreeTierExceeded, BudgetExceeded, APILimitExceeded) as e:
            gemini_failed_reason = f"rate/budget: {e}"
            _log(f"Gemini rate/budget limited for {caller}: {e}")
        except Exception as e:
            gemini_failed_reason = f"error: {e}"
            _log(f"Gemini error for {caller}: {e}")
    else:
        gemini_failed_reason = "no model provided"

    # --- Attempts 2+: stacked free providers, then the local floor ---
    # Each provider is an independent free rate-limit pool, so trying them in
    # turn spreads the daily 40-video burst across separate token/min caps — no
    # single provider's throttle drops a video. Skip any provider whose per-
    # request token ceiling this request would blow (it'd 429 regardless), and
    # move straight to the next pool on any failure. Local Ollama is the floor.
    est_tokens = _estimate_tokens(prompt)
    provider_failures = []

    for p in _HTTP_PROVIDERS:
        if not _load_key(p["key_env"]):
            continue  # not configured — skip silently
        if est_tokens > p["ceiling"]:
            _log(f"Skipping {p['name']} for {caller}: ~{est_tokens} tok > ceiling {p['ceiling']}")
            continue
        result = _http_provider_generate(p, prompt, max_tokens=max_tokens, timeout=timeout)
        if result:
            _log(f"{p['name']} succeeded for {caller}")
            return result
        provider_failures.append(p["name"])

    # Local Ollama floor — always-available, no rate limit.
    local_failed_reason = None
    if _LOCAL_ENABLED:
        result = _ollama_generate(prompt, max_tokens=max_tokens)
        if result:
            _log(f"Local ({_LOCAL_MODEL}) succeeded for {caller}")
            return result
        local_failed_reason = "local unreachable/empty (is Ollama running?)"
    else:
        local_failed_reason = "disabled (ENABLE_LOCAL_FALLBACK=0)"

    # --- All providers failed ---
    _log(
        f"ALL PROVIDERS FAILED for {caller} (~{est_tokens} tok) — "
        f"gemini=({gemini_failed_reason}) "
        f"http=({', '.join(provider_failures) or 'none configured'}) "
        f"local=({local_failed_reason}). "
        f"Skipping item (no raw-transcript fallback)."
    )

    if _allow_extractive:
        # Opt-in only — emits raw-ish transcript text. Off by default because
        # it produces incomplete, disfluency-laden output that's worse than
        # silence.
        transcript = _extract_transcript_from_prompt(prompt)
        if transcript:
            _log(f"ALLOW_EXTRACTIVE=1: emitting extractive summary for {caller}")
            return _extractive_summary(transcript)

    return None


def _extract_transcript_from_prompt(prompt: str) -> Optional[str]:
    """Pull the transcript/article text out of the prompt for extractive fallback."""
    # Look for common markers in our prompts
    for marker in ["TRANSCRIPT:\n", "Transcript:\n", "Article Content:\n"]:
        idx = prompt.find(marker)
        if idx != -1:
            return prompt[idx + len(marker):]
    return None
