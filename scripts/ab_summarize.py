#!/usr/bin/env python3
"""A/B the briefing summarizer: two free-chain candidates (or, only on request, Gemini) on one day's videos.

ZERO-SPEND BY DEFAULT. Gemini is a paid API and is only called with --with-gemini;
the normal comparison is free provider A vs free provider B.

Rebuilds the exact prompt the daemon uses (SourceFetcher._summarize_youtube with
custom_instructions.txt), fetches the transcripts for the videos the briefing
processed on --date (from processed_videos.json — transcripts are not cached, so
they are re-fetched with yt-dlp), runs BOTH models on the same prompt, and writes
a side-by-side markdown for Bradley to read/listen through.

    python3 scripts/ab_summarize.py                       # yesterday: A=groq gpt-oss-120b vs B=cloudflare gpt-oss-120b
    python3 scripts/ab_summarize.py --a groq:openai/gpt-oss-120b --b openrouter:nvidia/nemotron-3-super-120b-a12b:free
    python3 scripts/ab_summarize.py --with-gemini --limit 3  # PAID: Gemini as side A (only when explicitly wanted)

Nothing here touches the daemon or the live chain.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(HERE), "daily_audio_briefing")
sys.path.insert(0, APP)
os.environ.setdefault("DEBUG_FALLBACK", "0")

import llm_fallback  # noqa: E402
from source_fetcher import SourceFetcher  # noqa: E402

# gemini-2.5-flash list price, USD per 1M tokens (text). Used only for the estimate.
GEMINI_IN_PER_M, GEMINI_OUT_PER_M = 0.30, 2.50

FILLERS = re.compile(r"\b(um+|uh+|you know|i mean|sort of|kind of|hey guys|what's up everyone)\b", re.I)
PROMO = re.compile(r"\b(discord|telegram|patreon|subscribe|discount code|promo code|sponsor(ed)?|use code)\b", re.I)
TA = re.compile(r"\b(support|resistance|RSI|MACD|candlestick|order block|price target)\b", re.I)


def _oembed(video_id):
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": "daily-audio-briefing/ab/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        return d.get("title") or video_id, d.get("author_name") or ""
    except Exception:
        return video_id, ""


def _videos_for(date):
    with open(os.path.join(APP, "processed_videos.json")) as f:
        d = json.load(f)
    return [vid for vid, meta in d.get("videos", {}).items() if meta.get("processed_date") == date]


def _capture_prompt(fetcher, title, transcript, instructions, url, channel):
    """Run the real summarizer with the chain stubbed out; return the prompt it built."""
    box = {}

    def spy(prompt, gemini_model=None, caller="", timeout=120, max_tokens=4096):
        box["prompt"] = prompt
        return None

    real = llm_fallback.generate_with_fallback
    llm_fallback.generate_with_fallback = spy
    try:
        fetcher._summarize_youtube(title, transcript, instructions, source_url=url, channel_name=channel)
    finally:
        llm_fallback.generate_with_fallback = real
    return box.get("prompt")


def _gemini(prompt, model_name, api_key):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    t0 = time.monotonic()
    try:
        text = (model.generate_content(prompt, request_options={"timeout": 120}).text or "").strip()
        err = None
    except Exception as e:
        text, err = "", f"{type(e).__name__}: {e}"
    return text, time.monotonic() - t0, err


def _candidate(prompt, spec):
    name, model = spec.split(":", 1)
    p = next((x for x in llm_fallback._HTTP_PROVIDERS if x["name"] == name), None)
    if p is None:
        sys.exit(f"unknown provider {name!r}; choose from {[x['name'] for x in llm_fallback._HTTP_PROVIDERS]}")
    if not llm_fallback._load_key(p["key_env"]):
        sys.exit(f"{p['key_env']} is not set in .env — cannot run {spec}")
    t0 = time.monotonic()
    text = llm_fallback._http_provider_generate(p, prompt, max_tokens=4096, timeout=180, model=model)
    return (text or "").strip(), time.monotonic() - t0, None if text else "provider returned nothing (see fetch_debug.log)"


def _checks(text):
    """Cheap objective signals; the real judgement is Bradley's ear."""
    return {
        "words": len(text.split()),
        "markdown chars": len(re.findall(r"[*#]|^\s*[-•]\s", text, re.M)),
        "digits left": len(re.findall(r"\d", text)),
        "filler words": len(FILLERS.findall(text)),
        "promo terms": len(PROMO.findall(text)),
        "TA terms": len(TA.findall(text)),
        "preamble": int(bool(re.match(r"\s*(here('s| is)|this (video|transcript)|in this video|summary:)", text, re.I))),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default=(dt.date.today() - dt.timedelta(days=1)).isoformat())
    ap.add_argument("--a", default="groq:openai/gpt-oss-120b", help="side A: <provider>:<model> from llm_fallback._HTTP_PROVIDERS")
    ap.add_argument("--b", "--candidate", dest="candidate", default="cloudflare:@cf/openai/gpt-oss-120b", help="side B: <provider>:<model>")
    ap.add_argument("--with-gemini", action="store_true", help="PAID: use Gemini as side A instead of --a (costs money; off by default)")
    ap.add_argument("--gemini-model", default="gemini-2.5-flash")
    ap.add_argument("--limit", type=int, default=0, help="only the first N videos")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "docs", "ab"))
    args = ap.parse_args()

    use_gemini = args.with_gemini
    api_key = (llm_fallback._load_key("GEMINI_API_KEY") or "") if use_gemini else ""
    if use_gemini and not api_key:
        sys.exit("GEMINI_API_KEY not set")
    side_a = args.gemini_model if use_gemini else args.a
    with open(os.path.join(APP, "custom_instructions.txt")) as f:
        instructions = f.read()

    ids = _videos_for(args.date)
    if args.limit:
        ids = ids[: args.limit]
    if not ids:
        sys.exit(f"no processed videos on {args.date} in processed_videos.json")
    print(f"{len(ids)} videos processed on {args.date}; A={side_a}{' (PAID)' if use_gemini else ''}; B={args.candidate}")

    fetcher = SourceFetcher(api_key="", model_name=args.gemini_model, data_dir=APP)
    rows, cost, skipped = [], 0.0, []
    for i, vid in enumerate(ids, 1):
        url = f"https://www.youtube.com/watch?v={vid}"
        title, channel = _oembed(vid)
        print(f"[{i}/{len(ids)}] {title[:70]} — fetching transcript...", flush=True)
        tx = fetcher._get_youtube_transcript(vid)
        if not tx:
            skipped.append((title, url, "no transcript (yt-dlp)"))
            continue
        prompt = _capture_prompt(fetcher, title, tx, instructions, url, channel)
        if not prompt:
            skipped.append((title, url, "prompt capture failed"))
            continue
        row = {"title": title, "channel": channel, "url": url, "transcript_chars": len(tx), "prompt_chars": len(prompt)}
        if use_gemini:
            text, secs, err = _gemini(prompt, args.gemini_model, api_key)
            cost += len(prompt) / 4 / 1e6 * GEMINI_IN_PER_M + len(text) / 4 / 1e6 * GEMINI_OUT_PER_M
        else:
            text, secs, err = _candidate(prompt, args.a)
        row["A"] = {"model": side_a, "text": text, "secs": secs, "err": err, "checks": _checks(text)}
        print(f"    A {side_a}: {len(text)} chars in {secs:.1f}s {err or ''}")
        text, secs, err = _candidate(prompt, args.candidate)
        row["B"] = {"model": args.candidate, "text": text, "secs": secs, "err": err, "checks": _checks(text)}
        print(f"    B {args.candidate}: {len(text)} chars in {secs:.1f}s {err or ''}")
        rows.append(row)

    os.makedirs(args.out, exist_ok=True)
    slug = lambda x: re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")
    path = os.path.join(args.out, f"{args.date}_{slug(side_a)}-vs-{slug(args.candidate)}.md")
    with open(path, "w") as f:
        f.write(f"# Summarizer A/B — {args.date}\n\n")
        f.write(f"- **A** = `{side_a}`" + (f" (PAID Gemini; est. cost this run **${cost:.4f}**)\n" if use_gemini else " (free chain)\n"))
        f.write(f"- **B** = `{args.candidate}` (free chain)\n")
        f.write(f"- Same prompt as the daemon (`SourceFetcher._summarize_youtube` + `custom_instructions.txt`), {len(rows)} videos, {len(skipped)} skipped.\n")
        f.write("- Automated checks are only hints. Judge each pair on: **omit rules obeyed** (no promo, no TA, no price talk, no politics-only), **reads well aloud** (no markdown, numbers written out, no filler), **nothing important missing**.\n\n")
        f.write("## Scorecard\n\n| # | Video | A words / A secs | B words / B secs | A flags | B flags |\n|---|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            fl = lambda c: ", ".join(f"{k} {v}" for k, v in c["checks"].items() if k not in ("words",) and v) or "clean"
            a = r.get("A")
            f.write(f"| {i} | {r['title'][:50]} | {a['checks']['words']} / {a['secs']:.0f}s | "
                    f"{r['B']['checks']['words']} / {r['B']['secs']:.0f}s | {fl(a)} | {fl(r['B'])} |\n")
        f.write("\n")
        for i, r in enumerate(rows, 1):
            f.write(f"## {i}. {r['title']}\n\n{r['channel']} · {r['url']} · transcript {r['transcript_chars']:,} chars\n\n")
            for side in ("A", "B"):
                s = r.get(side)
                if not s:
                    continue
                f.write(f"### {side} — `{s['model']}` ({s['secs']:.1f}s)\n\n")
                f.write(f"> {s['err']}\n\n" if s["err"] else "")
                f.write((s["text"] or "_(empty)_") + "\n\n")
            f.write("**Verdict:** [ ] A better  [ ] B better  [ ] tie — notes:\n\n---\n\n")
        if skipped:
            f.write("## Skipped\n\n" + "".join(f"- {t} — {u} — {why}\n" for t, u, why in skipped))
    print(f"\nwrote {path}" + (f"  (Gemini est. cost ${cost:.4f})" if use_gemini else "  ($0 spent)"))


if __name__ == "__main__":
    main()
