"""
LLM Fallback Chain — Gemini → stacked free providers → local Ollama.

Provides a single generate_with_fallback() that tries providers in order, first
success wins. Gemini is first (off by default under the zero-spend budget), then
each configured free OpenAI-compatible provider in ``_HTTP_PROVIDERS`` (Cerebras,
Cloudflare, Groq, SambaNova, Mistral, Ollama Cloud, OpenRouter — enable one by
adding its key to .env), then local Ollama (gpt-oss:20b-tuned) as the always-
available, no-rate-limit floor. Stacking independent free tiers stops the daily
burst from 429-dropping videos on any single provider's tokens/min cap.

Override any provider model via the matching *_MODEL env var; local tier via
ENABLE_LOCAL_FALLBACK, OLLAMA_HOST, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT.

If all providers fail, ``generate_with_fallback`` returns None so the caller can
skip the item. The previous "extractive" fallback (first-25-sentences of the raw
transcript) was removed because it silently emitted unsummarized, disfluency-
laden transcript text into the audio brief. Set ALLOW_EXTRACTIVE=1 to opt back in.
"""

import os
import re
from typing import Optional

# Default to ON — fall-through events are rare and important. Set
# DEBUG_FALLBACK=0 in the environment to silence them.
_debug = os.environ.get("DEBUG_FALLBACK", "1").lower() in ("1", "true", "yes")
_allow_extractive = os.environ.get("ALLOW_EXTRACTIVE", "").lower() in ("1", "true", "yes")


def _log(msg: str):
    if _debug:
        # Print to stdout (captured by the scheduler/web log) AND tee into
        # fetch_debug.log so post-mortems can see why a brief came up empty.
        print(f"[LLM Fallback] {msg}")
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
# data (Groq, Cerebras, Cloudflare, SambaNova, Ollama Cloud), or training is
# user-disabled (Mistral, OpenRouter). Add a key to .env to enable a provider;
# providers without a key are skipped silently.
#
# Ordered by priority — highest sustained throughput first. `ceiling` is the
# per-request token cap above which a provider would 429 on its per-minute
# limit regardless of pacing, so we skip it for oversized requests.
# Override any model via the matching *_MODEL env var.
# ---------------------------------------------------------------------------
import json as _json
import urllib.request as _urlreq
import urllib.error as _urlerr

_HTTP_PROVIDERS = [
    {"name": "cerebras",     "key_env": "CEREBRAS_API_KEY",   "ceiling": 60000,
     "base": "https://api.cerebras.ai/v1",
     "model_env": "CEREBRAS_MODEL",     "model": "gpt-oss-120b"},
    {"name": "cloudflare",   "key_env": "CF_API_TOKEN",       "ceiling": 60000,
     "base": "https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1",
     "model_env": "CF_MODEL",           "model": "@cf/nvidia/nemotron-3-120b-a12b"},
    {"name": "groq",         "key_env": "GROQ_API_KEY",       "ceiling": 10000,
     "base": "https://api.groq.com/openai/v1",
     "model_env": "GROQ_MODEL",         "model": "openai/gpt-oss-120b"},
    {"name": "sambanova",    "key_env": "SAMBANOVA_API_KEY",  "ceiling": 16000,
     "base": "https://api.sambanova.ai/v1",
     "model_env": "SAMBANOVA_MODEL",    "model": "Meta-Llama-3.3-70B-Instruct"},
    {"name": "mistral",      "key_env": "MISTRAL_API_KEY",    "ceiling": 30000,
     "base": "https://api.mistral.ai/v1",
     "model_env": "MISTRAL_MODEL",      "model": "mistral-medium-latest"},
    {"name": "ollama_cloud", "key_env": "OLLAMA_API_KEY",     "ceiling": 60000,
     "base": "https://ollama.com/v1",
     "model_env": "OLLAMA_CLOUD_MODEL", "model": "gpt-oss:120b"},
    {"name": "openrouter",   "key_env": "OPENROUTER_API_KEY", "ceiling": 30000,
     "base": "https://openrouter.ai/api/v1",
     "model_env": "OPENROUTER_MODEL",   "model": "meta-llama/llama-3.3-70b-instruct:free"},
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


def _http_provider_generate(p: dict, prompt: str, max_tokens: int = 4096,
                            timeout: int = 120) -> Optional[str]:
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
    model = os.environ.get(p.get("model_env", "")) or p["model"]
    payload = _json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "daily-audio-briefing/1.0",
        "Authorization": f"Bearer {key}",
    }
    req = _urlreq.Request(base + "/chat/completions", data=payload, headers=headers)
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            data = _json.loads(resp.read())
        msg = (data.get("choices") or [{}])[0].get("message", {})
        # gpt-oss/reasoning models may leave content empty and use reasoning fields.
        text = (msg.get("content") or msg.get("reasoning_content")
                or msg.get("reasoning") or "").strip()
        if text:
            _log(f"{p['name']} ({model}) returned {len(text)} chars")
            return text
        _log(f"{p['name']} returned empty response")
        return None
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
) -> Optional[str]:
    """Try Gemini → stacked free providers → local Ollama; first success wins.

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

    Returns:
        Generated text, or None if all providers fail.
    """
    gemini_failed_reason: Optional[str] = None

    # --- Attempt 1: Gemini (free tier) ---
    if gemini_model is not None:
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
        result = _http_provider_generate(p, prompt, timeout=timeout)
        if result:
            _log(f"{p['name']} succeeded for {caller}")
            return result
        provider_failures.append(p["name"])

    # Local Ollama floor — always-available, no rate limit.
    local_failed_reason = None
    if _LOCAL_ENABLED:
        result = _ollama_generate(prompt)
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
