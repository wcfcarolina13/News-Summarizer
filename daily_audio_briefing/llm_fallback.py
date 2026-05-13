"""
LLM Fallback Chain — Gemini (free tier) → Groq (free tier).

Provides a single generate() function that tries providers in order.
Each provider is only attempted if its API key is configured.

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


def _groq_generate(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """Call Groq's free-tier Llama model. Returns None on any failure."""
    client = _get_groq_client()
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        text = response.choices[0].message.content
        _log(f"Groq returned {len(text)} chars")
        return text
    except Exception as e:
        _log(f"Groq error: {e}")
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
    """Try Gemini → Groq → extractive, returning the first success.

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

    # --- Attempt 2: Groq (free tier) ---
    groq_result = _groq_generate(prompt)
    if groq_result:
        _log(f"Groq fallback succeeded for {caller}")
        return groq_result
    if _get_groq_client() is None:
        groq_failed_reason = "GROQ_API_KEY not configured"
    else:
        groq_failed_reason = "groq returned nothing (rate-limited or error)"

    # --- Both providers failed ---
    _log(
        f"BOTH PROVIDERS FAILED for {caller} — "
        f"gemini=({gemini_failed_reason}) groq=({groq_failed_reason}). "
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
