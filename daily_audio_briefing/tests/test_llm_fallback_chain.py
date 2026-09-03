"""Chain shape + plumbing tests for llm_fallback (2026-09-03 changes).

Cerebras is gone (402 on every completion since 2026-08-18), Groq leads,
max_tokens reaches the HTTP providers and the local floor, and the
DAB_SUMMARIZER A/B switch is honoured only by summarizer call sites.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import llm_fallback  # noqa: E402


def _names():
    return [p["name"] for p in llm_fallback._HTTP_PROVIDERS]


def test_cerebras_removed_and_groq_leads():
    assert "cerebras" not in _names()
    assert _names()[:2] == ["groq", "cloudflare"]


def test_openrouter_default_is_a_free_non_reasoning_model():
    p = next(x for x in llm_fallback._HTTP_PROVIDERS if x["name"] == "openrouter")
    assert p["model"].endswith(":free")
    assert "llama-3.3-70b" not in p["model"]  # retired from the free tier 2026-09


@pytest.fixture
def isolated(monkeypatch):
    """Every provider 'configured', Gemini off, local floor off, no override."""
    monkeypatch.setattr(llm_fallback, "_load_key", lambda env: "k")
    monkeypatch.setattr(llm_fallback, "_GEMINI_ENABLED", False)
    monkeypatch.setattr(llm_fallback, "_LOCAL_ENABLED", False)
    monkeypatch.setattr(llm_fallback, "_debug", False)
    monkeypatch.delenv("DAB_SUMMARIZER", raising=False)


def test_max_tokens_reaches_http_provider(isolated, monkeypatch):
    seen = {}

    def fake(p, prompt, max_tokens=4096, timeout=120, model=None):
        seen.update(name=p["name"], max_tokens=max_tokens, model=model)
        return "out"

    monkeypatch.setattr(llm_fallback, "_http_provider_generate", fake)
    assert llm_fallback.generate_with_fallback("p", caller="x", max_tokens=8000) == "out"
    assert seen == {"name": "groq", "max_tokens": 8000, "model": None}


def test_max_tokens_reaches_local_floor(isolated, monkeypatch):
    monkeypatch.setattr(llm_fallback, "_http_provider_generate", lambda *a, **k: None)
    monkeypatch.setattr(llm_fallback, "_LOCAL_ENABLED", True)
    seen = {}

    def fake_local(prompt, max_tokens=4096):
        seen["max_tokens"] = max_tokens
        return "local"

    monkeypatch.setattr(llm_fallback, "_ollama_generate", fake_local)
    assert llm_fallback.generate_with_fallback("p", caller="x", max_tokens=6000) == "local"
    assert seen["max_tokens"] == 6000


def test_ceiling_skips_groq_for_long_prompt(isolated, monkeypatch):
    calls = []
    monkeypatch.setattr(llm_fallback, "_http_provider_generate",
                        lambda p, *a, **k: calls.append(p["name"]) or "ok")
    llm_fallback.generate_with_fallback("x" * 60000, caller="x")  # ~15k tokens
    assert calls == ["cloudflare"]


def test_summarizer_override_tried_first_for_summarizer_caller(isolated, monkeypatch):
    monkeypatch.setenv("DAB_SUMMARIZER", "cloudflare:@cf/moonshotai/kimi-k2.6")
    calls = []

    def fake(p, prompt, max_tokens=4096, timeout=120, model=None):
        calls.append((p["name"], model))
        return "ok"

    monkeypatch.setattr(llm_fallback, "_http_provider_generate", fake)
    out = llm_fallback.generate_with_fallback("p", caller="fetcher._summarize_yt")
    assert out == "ok"
    assert calls == [("cloudflare", "@cf/moonshotai/kimi-k2.6")]


def test_summarizer_override_falls_back_to_chain_on_failure(isolated, monkeypatch):
    monkeypatch.setenv("DAB_SUMMARIZER", "openrouter:nvidia/nemotron-3-super-120b-a12b:free")
    calls = []

    def fake(p, prompt, max_tokens=4096, timeout=120, model=None):
        calls.append((p["name"], model))
        return None if model else "ok"

    monkeypatch.setattr(llm_fallback, "_http_provider_generate", fake)
    assert llm_fallback.generate_with_fallback("p", caller="fetcher._summarize_article") == "ok"
    # override first (model split on the FIRST colon so ':free' survives), then the chain
    assert calls[0] == ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free")
    assert calls[1] == ("groq", None)


def test_summarizer_override_ignored_for_cleaning_caller(isolated, monkeypatch):
    monkeypatch.setenv("DAB_SUMMARIZER", "cloudflare:@cf/moonshotai/kimi-k2.6")
    calls = []
    monkeypatch.setattr(llm_fallback, "_http_provider_generate",
                        lambda p, *a, **k: calls.append((p["name"], k.get("model"))) or "ok")
    llm_fallback.generate_with_fallback("p", caller="audio_jobs.clean_text")
    assert calls == [("groq", None)]


def test_summarizer_override_unknown_provider_is_ignored(isolated, monkeypatch):
    monkeypatch.setenv("DAB_SUMMARIZER", "cerebras:gpt-oss-120b")
    assert llm_fallback._summarizer_override() is None
    monkeypatch.setenv("DAB_SUMMARIZER", "garbage")
    assert llm_fallback._summarizer_override() is None
