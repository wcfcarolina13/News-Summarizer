"""
LLM Fallback Chain — Gemini (free tier) → Groq (free tier) → local Ollama.

Provides a single generate() function that tries providers in order.
Each provider is only attempted if it is configured/reachable. The local
Ollama tier (gpt-oss:20b-tuned by default) is a zero-cost, no-rate-limit
safety net so a Groq throttle or outage never silently drops an item.
Override via env: GROQ_MODEL, GROQ_MAX_RETRIES, ENABLE_LOCAL_FALLBACK,
OLLAMA_HOST, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT.

If both providers fail, ``generate_with_fallback`` returns None so the caller
can skip the item. The previous "extractive" fallback (first-25-sentences of
the raw transcript) was removed because it silently emitted unsummarized,
disfluency-laden transcript text into the audio brief.

Set ALLOW_EXTRACTIVE=1 in the environment to opt back into the old behaviour
if you really want a degraded-but-present output.
"""

import os
import re
import time
import threading
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
# Groq provider (free tier: 30 RPM, 14.4K tokens/min on Llama models)
# ---------------------------------------------------------------------------
_groq_client = None
_groq_lock = threading.Lock()


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client

    key = os.environ.get("GROQ_API_KEY") or ""
    if not key:
        # Also check .env file in the script directory
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("'\"")
                        break

    if not key:
        return None

    with _groq_lock:
        if _groq_client is not None:
            return _groq_client
        try:
            from groq import Groq
            _groq_client = Groq(api_key=key)
            _log("Groq client initialized")
            return _groq_client
        except ImportError:
            _log("groq SDK not installed — pip install groq")
            return None
        except Exception as e:
            _log(f"Groq init error: {e}")
            return None


_GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
_GROQ_MAX_RETRIES = int(os.environ.get("GROQ_MAX_RETRIES", "3"))
# Groq free tier is ~12,000 tokens/minute. A request near/over that 429s no
# matter how it's paced, so we route oversized requests to the local model
# first and don't waste a doomed Groq attempt + retry on them. Default 10K
# leaves headroom under the 12K TPM ceiling for prompt + output.
_GROQ_TPM_SAFE_TOKENS = int(os.environ.get("GROQ_TPM_SAFE_TOKENS", "10000"))


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) — good enough for routing."""
    return len(text) // 4


def _is_rate_limit_error(e: Exception) -> bool:
    """Detect a 429 / rate-limit error across groq SDK versions."""
    if e.__class__.__name__ in ("RateLimitError", "TooManyRequests"):
        return True
    if getattr(e, "status_code", None) == 429 or getattr(e, "code", None) == 429:
        return True
    return "rate limit" in str(e).lower() or "429" in str(e)


def _retry_after_seconds(e: Exception, attempt: int) -> float:
    """Honour a Retry-After header if present; else exponential backoff (capped)."""
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            ra = resp.headers.get("retry-after")
            if ra:
                return min(float(ra), 30.0)
        except Exception:
            pass
    return min(2.0 * (2 ** attempt), 30.0)  # 2s, 4s, 8s … capped at 30s


def _groq_generate(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """Call Groq's free-tier Llama model, retrying on 429. None on hard failure.

    The free tier throttles on tokens-per-minute, which is easy to hit on a burst
    of long transcripts. Without retry a throttled video was silently dropped.
    """
    client = _get_groq_client()
    if not client:
        return None

    for attempt in range(_GROQ_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            text = response.choices[0].message.content
            _log(f"Groq returned {len(text)} chars")
            return text
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < _GROQ_MAX_RETRIES - 1:
                wait = _retry_after_seconds(e, attempt)
                _log(f"Groq 429/rate-limited (attempt {attempt + 1}/{_GROQ_MAX_RETRIES}); retrying in {wait:.0f}s")
                time.sleep(wait)
                continue
            _log(f"Groq error: {e}")
            return None
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
    """Try Gemini → (Groq/local, ordered by size) → skip, first success wins.

    Gemini is tried first when a model is provided and it's within budget.
    The Groq/local order is token-aware: requests that fit Groq's free-tier
    ~12K-tokens/min window try Groq first (fast) then local; oversized requests
    that would 429 regardless go local-first (no limits) with Groq as a long
    shot. This stops the daily burst from 429-dropping videos.

    Args:
        prompt: The full prompt including transcript.
        gemini_model: A google.generativeai model instance (or None to skip).
        caller: Caller identifier for tracking.
        timeout: Timeout for Gemini calls.

    Returns:
        Generated text, or None if all providers fail.
    """
    gemini_failed_reason: Optional[str] = None
    groq_failed_reason: Optional[str] = None

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

    # --- Attempts 2 & 3: Groq + local, ordered by request size ---
    # Groq is fast but capped at ~12K tokens/min on the free tier. For requests
    # that fit, try Groq first (speed) then local. For oversized requests that
    # would 429 regardless of pacing, go local first (no limits) and only try
    # Groq as a long shot — so the daily 40-video burst never drops a video and
    # never wastes time on a doomed Groq call.
    groq_failed_reason = None
    local_failed_reason = None
    est_tokens = _estimate_tokens(prompt)

    def _try_groq():
        nonlocal groq_failed_reason
        result = _groq_generate(prompt)
        if result:
            _log(f"Groq succeeded for {caller}")
            return result
        if _get_groq_client() is None:
            groq_failed_reason = "GROQ_API_KEY not configured"
        else:
            groq_failed_reason = "groq returned nothing (rate-limited or error)"
        return None

    def _try_local():
        nonlocal local_failed_reason
        if not _LOCAL_ENABLED:
            local_failed_reason = "disabled (ENABLE_LOCAL_FALLBACK=0)"
            return None
        result = _ollama_generate(prompt)
        if result:
            _log(f"Local ({_LOCAL_MODEL}) succeeded for {caller}")
            return result
        local_failed_reason = "local LLM unreachable/empty (is Ollama running?)"
        return None

    if est_tokens <= _GROQ_TPM_SAFE_TOKENS:
        order = [_try_groq, _try_local]
    else:
        _log(f"Request ~{est_tokens} tok > Groq TPM-safe {_GROQ_TPM_SAFE_TOKENS} "
             f"for {caller}; routing to local first")
        order = [_try_local, _try_groq]

    for attempt in order:
        result = attempt()
        if result:
            return result

    # --- All providers failed ---
    _log(
        f"ALL PROVIDERS FAILED for {caller} (~{est_tokens} tok) — "
        f"gemini=({gemini_failed_reason}) groq=({groq_failed_reason}) "
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
