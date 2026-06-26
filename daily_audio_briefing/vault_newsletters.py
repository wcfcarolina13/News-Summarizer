"""Inject already-processed Pontus newsletter notes into the audio briefing.

The Pontus vault pipeline already fetches + summarizes these newsletters into
`vault/<NN>-<Source>/<Source>-YYYY-MM-DD.md`. Rather than have the audio app
re-fetch and re-summarize them (double Gemini cost), we read those finished
notes and emit them as FetchedItems for the briefing's TTS step.

Each issue is voiced exactly once via a tiny cache (`voiced_newsletter_notes.json`).
We mark an issue voiced at build time — safe here (unlike ephemeral video
transcripts) because the vault note is a durable source: a failed delivery never
loses the content, it just misses one day's audio.
"""
import os
import re
import json
from datetime import datetime, timedelta

from source_fetcher import FetchedItem, SourceType

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")   # [[a|b]] -> a
_MDLINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")               # [t](u)  -> t
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# (vault subdir, spoken source name) — the newsletters approved for audio.
DEFAULT_SPECS = [("12-Batch", "The Batch"), ("15-DanGo", "Dan Go")]


def _split_frontmatter(raw):
    """(frontmatter_dict, body). Simple line parser — not full YAML."""
    fm, body = {}, raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            for line in raw[3:end].splitlines():
                if ":" in line and not line.lstrip().startswith("#"):
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip('"').strip("'")
            body = raw[end + 4:]
    return fm, body


def _note_date(fm, filename):
    for key in ("date_published", "date_added", "date"):
        m = _DATE.search(str(fm.get(key, "")))
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                pass
    m = _DATE.search(filename)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return None


def _clean_body(body):
    """Strip markdown/wikilinks/nav so the note reads cleanly as speech."""
    out = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("---", "←", "<!--", "![", "**Source:**", "|")):
            continue
        s = re.sub(r"^>+\s*", "", s)        # blockquote -> keep its text (the summary)
        s = re.sub(r"^#{1,6}\s*", "", s)    # headings
        s = re.sub(r"^[-*]\s+", "", s)      # bullets
        s = s.replace("**", "").replace("`", "")
        s = _WIKILINK.sub(r"\1", s)
        s = _MDLINK.sub(r"\1", s)
        s = s.strip()
        if len(s) >= 2:
            out.append(s)
    return " ".join(out).strip()


def load_vault_newsletter_items(data_dir, vault_dir, specs=None, lookback_days=10):
    """Return FetchedItems for vault newsletter issues not yet voiced (within lookback)."""
    specs = specs or DEFAULT_SPECS
    cache_path = os.path.join(data_dir, "voiced_newsletter_notes.json")
    try:
        voiced = set(json.load(open(cache_path, encoding="utf-8")).get("paths", []))
    except Exception:
        voiced = set()

    cutoff = datetime.now() - timedelta(days=lookback_days)
    items, newly = [], []
    for subdir, display in specs:
        d = os.path.join(vault_dir, subdir)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md") or "Log" in fn:
                continue
            path = os.path.join(d, fn)
            if path in voiced:
                continue
            try:
                raw = open(path, encoding="utf-8").read()
            except Exception:
                continue
            fm, body = _split_frontmatter(raw)
            dt = _note_date(fm, fn)
            if dt is None or dt < cutoff:
                continue
            text = _clean_body(body)
            if len(text) < 80:
                continue
            items.append(FetchedItem(
                title=(fm.get("title") or fn[:-3]).strip(),
                url=fm.get("url", ""),
                content=text,
                source_name=display,
                source_type=SourceType.RSS,   # renders under "From RSS feeds:" like the Zvi
                published_date=dt,
                summary=text,
                metadata={"origin": "vault", "path": path},
            ))
            newly.append(path)

    if newly:
        try:
            voiced.update(newly)
            json.dump({"paths": sorted(voiced)}, open(cache_path, "w", encoding="utf-8"), indent=2)
        except Exception:
            pass
    return items
