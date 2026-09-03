#!/usr/bin/env python3
"""Stress-test free OpenAI-compatible LLM providers for the briefing fallback stack.

Architecture-agnostic: measures each provider's real latency, rate-limit headers,
and burst throughput so we can pick the stack (and order) on data, not guesses.
Only stdlib — no new deps. Providers without a key in .env are skipped.

Usage:
    python3 stress_test_providers.py probe                 # 1 call/provider: latency + limits
    python3 stress_test_providers.py burst --provider groq --n 25 --concurrency 5
    python3 stress_test_providers.py simulate --videos 40   # model the daily briefing burst
"""
import argparse
import json
import os
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed


def _load_env():
    """Load KEY=VALUE pairs from the daemon's .env (symlinked to App Support)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


# Audited-safe OpenAI-compatible providers (see security audit 2026-06-03).
# Model ids are best-effort current free models; a 404 from probe means update it.
PROVIDERS = [
    {"id": "groq",        "key_env": "GROQ_API_KEY",       "model": "openai/gpt-oss-120b",
     "base": "https://api.groq.com/openai/v1"},
    {"id": "cerebras",    "key_env": "CEREBRAS_API_KEY",   "model": "gpt-oss-120b",
     "base": "https://api.cerebras.ai/v1"},
    {"id": "openrouter",  "key_env": "OPENROUTER_API_KEY", "model": "meta-llama/llama-3.3-70b-instruct:free",
     "base": "https://openrouter.ai/api/v1"},
    {"id": "mistral",     "key_env": "MISTRAL_API_KEY",    "model": "mistral-medium-latest",
     "base": "https://api.mistral.ai/v1"},
    {"id": "ollama_cloud","key_env": "OLLAMA_API_KEY",     "model": "gpt-oss:120b",
     "base": "https://ollama.com/v1"},
    # Cloudflare needs the account id spliced into the base URL.
    {"id": "cloudflare",  "key_env": "CF_API_TOKEN",       "model": "@cf/nvidia/nemotron-3-120b-a12b",
     "base": "https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1"},
    # Local floor — no key, must be running.
    {"id": "local_ollama","key_env": None,                 "model": "gpt-oss:20b-tuned",
     "base": "http://localhost:11434/v1"},
]


def available(p):
    """A provider is usable if its key (if any) and any URL placeholders resolve."""
    if p["key_env"] and not os.environ.get(p["key_env"]):
        return False
    if "{CF_ACCOUNT_ID}" in p["base"] and not os.environ.get("CF_ACCOUNT_ID"):
        return False
    return True


def _base_url(p):
    return p["base"].replace("{CF_ACCOUNT_ID}", os.environ.get("CF_ACCOUNT_ID", ""))


def make_prompt(approx_tokens):
    """Build a realistic summarization prompt of ~approx_tokens (≈4 chars/token)."""
    para = ("The host discusses macro conditions, central bank policy, equity earnings, "
            "and the broad market narrative for the week ahead, weighing risks and catalysts. ")
    body = (para * (max(1, approx_tokens * 4 // len(para))))[: approx_tokens * 4]
    return ("Summarize this transcript for an audio news briefing in flowing prose, "
            "omitting intraday technical analysis.\n\nTranscript:\n" + body)


def call_provider(p, prompt, max_tokens=400, timeout=120):
    """One OpenAI-style chat completion. Returns timing/status/rate-limit info."""
    url = _base_url(p) + "/chat/completions"
    payload = json.dumps({
        "model": p["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode()
    # A real User-Agent is required: several provider APIs are Cloudflare-fronted
    # and 403 (error 1010) a bare urllib UA. The SDKs send one; so must we.
    headers = {"Content-Type": "application/json", "User-Agent": "briefing-stress-test/1.0"}
    if p["key_env"]:
        headers["Authorization"] = f"Bearer {os.environ[p['key_env']]}"
    req = urllib.request.Request(url, data=payload, headers=headers)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            dt = time.monotonic() - t0
            msg = data.get("choices", [{}])[0].get("message", {})
            # gpt-oss/reasoning models sometimes leave content empty and put text
            # under reasoning/reasoning_content — count either as output.
            out = (msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or "")
            rl = {k.lower(): v for k, v in r.headers.items()
                  if "ratelimit" in k.lower() or k.lower() == "retry-after"}
            return {"ok": True, "status": 200, "latency": dt, "out_chars": len(out), "rate": rl, "err": None}
    except urllib.error.HTTPError as e:
        dt = time.monotonic() - t0
        rl = {k.lower(): v for k, v in e.headers.items()
              if "ratelimit" in k.lower() or k.lower() == "retry-after"} if e.headers else {}
        body = ""
        try:
            body = e.read().decode()[:160]
        except Exception:
            pass
        return {"ok": False, "status": e.code, "latency": dt, "out_chars": 0, "rate": rl,
                "err": f"{e.code} {body}"}
    except Exception as e:
        return {"ok": False, "status": None, "latency": time.monotonic() - t0,
                "out_chars": 0, "rate": {}, "err": f"{type(e).__name__}: {e}"}


def cmd_probe(args):
    prompt = make_prompt(args.tokens)
    print(f"PROBE — one {args.tokens}-token call per available provider\n")
    print(f"{'provider':14} {'status':7} {'lat(s)':7} {'out':5}  rate-limit headers / error")
    print("-" * 100)
    for p in PROVIDERS:
        if not available(p):
            print(f"{p['id']:14} {'SKIP':7} {'':7} {'':5}  (no {p['key_env']})")
            continue
        r = call_provider(p, prompt, max_tokens=args.max_tokens)
        rate = ", ".join(f"{k}={v}" for k, v in list(r["rate"].items())[:4]) or "-"
        info = rate if r["ok"] else r["err"]
        print(f"{p['id']:14} {str(r['status']):7} {r['latency']:<7.2f} {r['out_chars']:<5} {info[:70]}")


def cmd_burst(args):
    p = next((x for x in PROVIDERS if x["id"] == args.provider), None)
    if not p or not available(p):
        print(f"provider '{args.provider}' not available (key missing or unknown)"); return
    prompt = make_prompt(args.tokens)
    print(f"BURST — {args.n} reqs at {p['id']} ({p['model']}), concurrency={args.concurrency}\n")
    results = []
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(call_provider, p, prompt, args.max_tokens) for _ in range(args.n)]
        for f in as_completed(futs):
            results.append(f.result())
    wall = time.monotonic() - t0
    ok = sum(1 for r in results if r["ok"])
    r429 = sum(1 for r in results if r["status"] == 429)
    err = len(results) - ok - r429
    lats = sorted(r["latency"] for r in results if r["ok"])
    p50 = lats[len(lats) // 2] if lats else 0
    print(f"  ok={ok}  429={r429}  other_err={err}  wall={wall:.1f}s  p50_latency={p50:.2f}s")
    if r429 or err:
        for r in results:
            if not r["ok"]:
                print(f"    {r['status']}: {(r['err'] or '')[:90]}")
                break


def cmd_simulate(args):
    """Model the daily briefing: N videos, ~9K-token prompts, down the stack order."""
    stack = [p for p in PROVIDERS if available(p)]
    if not stack:
        print("no providers available"); return
    print(f"SIMULATE — {args.videos} videos (~{args.tokens}tok each) over stack: "
          f"{[p['id'] for p in stack]}\n")
    prompt = make_prompt(args.tokens)
    counts = {p["id"]: 0 for p in stack}
    drops = 0
    for _ in range(args.videos):
        placed = False
        for p in stack:                       # try each tier until one accepts
            r = call_provider(p, prompt, args.max_tokens)
            if r["ok"]:
                counts[p["id"]] += 1; placed = True; break
            if r["status"] != 429:            # non-429 error: try next tier too
                continue
        if not placed:
            drops += 1
    print("  served per provider:", {k: v for k, v in counts.items() if v})
    print(f"  DROPPED (all tiers failed): {drops}/{args.videos}")


if __name__ == "__main__":
    _load_env()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("probe"); pp.set_defaults(fn=cmd_probe)
    pb = sub.add_parser("burst"); pb.set_defaults(fn=cmd_burst)
    pb.add_argument("--provider", required=True)
    pb.add_argument("--n", type=int, default=20)
    pb.add_argument("--concurrency", type=int, default=5)
    ps = sub.add_parser("simulate"); ps.set_defaults(fn=cmd_simulate)
    ps.add_argument("--videos", type=int, default=40)
    for x in (pp, pb, ps):
        x.add_argument("--tokens", type=int, default=9000, help="approx prompt tokens")
        x.add_argument("--max-tokens", type=int, default=400, help="max output tokens")
    args = ap.parse_args()
    args.fn(args)
