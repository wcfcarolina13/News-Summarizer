"""Regression tests for the reasoning-leak guards.

Bug (2026-06-13): in cooldown mode every summary runs through gpt-oss reasoning
models. For one video the model fell into a repetition loop, never produced a
final answer, and `llm_fallback` returned its reasoning channel as the summary —
which got read aloud near the end of the briefing ("We need to summarize the
video transcript... Must obey formatting... Also avoid thirty thousand...").

Two layers now guard against this:
  1. llm_fallback only returns the final-answer channel and rejects truncated /
     looping output, falling through to the next provider.
  2. SourceFetcher._looks_like_reasoning_leak drops any summary that is actually
     leaked reasoning, as a backstop.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from source_fetcher import SourceFetcher
import llm_fallback

# Verbatim head of the real leak from 2026-06-13_News.txt (line 409).
REAL_LEAK = (
    "We need to summarize the video transcript, focusing on main points, "
    "takeaways, data, predictions, actionable recommendations, market sentiment, "
    "macro trends, entities. Must obey formatting: no markdown, no bullets, no "
    "hyphens, no special characters, pure prose, numbers written out. Must start "
    "directly with content. The user wants crypto, AI, geopolitics, finance."
)

# A real, clean summary from the same briefing.
REAL_SUMMARY = (
    "Japan amended its Financial Instruments and Exchange Act to treat crypto as a "
    "financial instrument, subjecting token issuers to insider trading rules and "
    "annual disclosures. The tax regime drops to a flat twenty point three percent "
    "with a three year loss carry forward, aligning crypto with equities. SBI "
    "Holdings filed for a spot Bitcoin and XRP exchange traded fund targeting five "
    "trillion yen within three years."
)

REPETITION_LOOP = " ".join(["Also avoid thirty thousand. Use thirty thousand."] * 80)


def _sf():
    return SourceFetcher(api_key="x", data_dir="/tmp")


def test_flags_real_meta_reasoning_leak():
    assert _sf()._looks_like_reasoning_leak(REAL_LEAK) is True


def test_passes_real_clean_summary():
    assert _sf()._looks_like_reasoning_leak(REAL_SUMMARY) is False


def test_flags_repetition_loop():
    assert _sf()._looks_like_reasoning_leak(REPETITION_LOOP) is True


def test_empty_summary_is_not_a_leak():
    assert _sf()._looks_like_reasoning_leak("") is False
    assert _sf()._looks_like_reasoning_leak(None) is False


def test_llm_fallback_degenerate_detector():
    assert llm_fallback._looks_degenerate(REPETITION_LOOP) is True
    assert llm_fallback._looks_degenerate(REAL_SUMMARY) is False
