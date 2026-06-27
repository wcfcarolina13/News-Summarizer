"""Reuse already-summarized local markdown notes as audio-briefing segments.

If you already summarize newsletters/articles into markdown elsewhere (any pipeline that
writes `<folder>/<name>-YYYY-MM-DD.md` with the summary in the body), this adapter voices
those finished notes directly instead of re-fetching and re-summarizing them (saving AI
cost). Configure it in `local_sources.json` (gitignored); see `local_sources.example.json`.
Disabled by default — absent config, missing base_dir, or no enabled folders = no-op.

Each note is voiced exactly once via a tiny cache (`voiced_newsletter_notes.json`). Marking
a note voiced at build time is safe here (unlike ephemeral transcripts) because the markdown
note is durable: a failed delivery misses one day's audio, never the content.
"""
import os
import re
import sys
import json
from datetime import datetime, timedelta

from source_fetcher import FetchedItem, SourceType

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")   # [[a|b]] -> a
_MDLINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")               # [t](u)  -> t
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# Raw links read terribly aloud: full URLs, and bare "domain.tld/path" forms (e.g. a DOI or
# "biohub.ai/tools/fold"). Requires a path after the TLD so bare domains in prose survive.
_URL = re.compile(r"https?://\S+|\b(?:[a-z0-9][a-z0-9-]*\.)+[a-z]{2,}/[^\s)]+", re.IGNORECASE)

_DEFAULT_DATE_KEYS = ("date_published", "date_added", "date")
_DEFAULT_EXCLUDES = ["Log"]
_CACHE_NAME = "voiced_newsletter_notes.json"
_CONFIG_NAME = "local_sources.json"

# Read-only artifacts that ruin TTS — a heading whose text matches stops the body (everything
# after is cross-reference navigation); meta/citation line prefixes are dropped outright.
_STOP_HEADINGS = ("connection points", "connection point", "related notes", "see also")
_META_MARKERS = ("items extracted from", "filtered for signal")
_CITATION_PREFIXES = ("reference:", "references:", "source:")  # leading '*' is stripped before match


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _app_support_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
    return os.path.expanduser("~/.daily-audio-briefing")


def _find_config(data_dir):
    """Locate local_sources.json: data_dir -> App Support -> script_dir. Path or None."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for d in (data_dir, _app_support_dir(), script_dir):
        if d:
            p = os.path.join(d, _CONFIG_NAME)
            if os.path.exists(p):
                return p
    return None


def _resolve_config(data_dir):
    """Return (base_dir, folders, lookback_days). base_dir='' or folders=[] => disabled."""
    cfg = {}
    path = _find_config(data_dir)
    if path:
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    # base_dir precedence: env LOCAL_MARKDOWN_DIR -> env PONTUS_VAULT_DIR (back-compat) -> config
    base_dir = (os.environ.get("LOCAL_MARKDOWN_DIR")
                or os.environ.get("PONTUS_VAULT_DIR")
                or cfg.get("base_dir") or "")
    base_dir = os.path.expanduser(base_dir) if base_dir else ""
    folders = [f for f in cfg.get("folders", []) if f.get("enabled", True)]
    lookback_days = _int(cfg.get("lookback_days", 10), 10)
    return base_dir, folders, lookback_days


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


def _note_date(fm, filename, date_keys, use_filename=True):
    for key in date_keys:
        m = _DATE.search(str(fm.get(key, "")))
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                pass
    if use_filename:
        m = _DATE.search(filename)
        if m:
            try:
                return datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                pass
    return None


def _clean_body(body):
    """Strip markdown/wikilinks/nav + read-only artifacts so the note reads as speech.

    Beyond inline markdown, this drops the things that ruin a TTS reading of a wiki note:
    the trailing "Connection Points" cross-reference block (and everything after it),
    pipeline meta-framing lines, academic citation/reference lines, and raw URLs/DOIs.
    """
    out = []
    for line in body.splitlines():
        s = line.strip()
        # Stop at a cross-reference / "see also" heading — the rest is read-only navigation.
        if re.sub(r"^#{1,6}\s*", "", s).strip().lower() in _STOP_HEADINGS:
            break
        if not s or s.startswith(("---", "←", "<!--", "![", "**Source:**", "|")):
            continue
        low = s.lower()
        if any(m in low for m in _META_MARKERS):       # "Items extracted from … filtered for signal."
            continue
        if low.lstrip("*").startswith(_CITATION_PREFIXES):  # "*Reference:* … https://doi.org/…"
            continue
        s = re.sub(r"^>+\s*", "", s)        # blockquote -> keep its text (the summary)
        s = re.sub(r"^#{1,6}\s*", "", s)    # headings
        s = re.sub(r"^[-*]\s+", "", s)      # bullets
        s = s.replace("**", "").replace("`", "")
        s = _WIKILINK.sub(r"\1", s)
        s = _MDLINK.sub(r"\1", s)
        s = _URL.sub("", s)                 # raw URLs/DOIs read as gibberish aloud
        s = re.sub(r"\s{2,}", " ", s).strip()
        if len(s) >= 2:
            out.append(s)
    return " ".join(out).strip()


def _clean_title(title, source_name):
    """Drop a leading 'SourceName —/:/-' prefix so audio doesn't name the source twice.

    The audio format already says "From {source_name}, {title}"; vault titles usually start
    with the source name too ("The Batch — 2026-06-26: Issue 359"), so strip that prefix.
    """
    t = (title or "").strip()
    if source_name:
        m = re.match(re.escape(source_name) + r"\s*[—:\-]+\s*", t, re.IGNORECASE)
        if m:
            t = t[m.end():].strip()
    return t


def load_local_markdown_items(data_dir, config=None):
    """FetchedItems for not-yet-voiced local markdown notes within the lookback window.

    config: optional {base_dir, folders[], lookback_days} (used by tests). When None it is
    resolved from local_sources.json + env overrides. Returns [] when disabled (no base_dir,
    base_dir not a directory, or no enabled folders).
    """
    if config is None:
        base_dir, folders, lookback_days = _resolve_config(data_dir)
    else:
        base_dir = os.path.expanduser(config.get("base_dir", "") or "")
        folders = [f for f in config.get("folders", []) if f.get("enabled", True)]
        lookback_days = _int(config.get("lookback_days", 10), 10)

    if not base_dir or not os.path.isdir(base_dir) or not folders:
        return []

    cache_path = os.path.join(data_dir, _CACHE_NAME)
    try:
        with open(cache_path, encoding="utf-8") as fh:
            voiced = set(json.load(fh).get("paths", []))
    except Exception:
        voiced = set()

    cutoff = datetime.now() - timedelta(days=lookback_days)
    items, newly = [], []
    for spec in folders:
        subdir = spec.get("subdir", "")
        display = spec.get("source_name") or subdir
        date_keys = tuple(spec.get("date_keys") or _DEFAULT_DATE_KEYS)
        use_filename = spec.get("date_from_filename", True)
        excludes = spec.get("exclude_filename_contains", _DEFAULT_EXCLUDES)
        min_chars = _int(spec.get("min_chars", 80), 80)

        d = os.path.join(base_dir, subdir)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            if any(x in fn for x in excludes):
                continue
            path = os.path.join(d, fn)
            if path in voiced:
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    raw = fh.read()
            except Exception:
                continue
            fm, body = _split_frontmatter(raw)
            dt = _note_date(fm, fn, date_keys, use_filename)
            if dt is None or dt < cutoff:
                continue
            text = _clean_body(body)
            if len(text) < min_chars:
                continue
            items.append(FetchedItem(
                title=_clean_title(fm.get("title") or fn[:-3], display),
                url=fm.get("url", ""),
                content=text,
                source_name=display,
                source_type=SourceType.RSS,   # renders under "From RSS feeds:"
                published_date=dt,
                summary=text,
                metadata={"origin": "local_markdown", "path": path},
            ))
            newly.append(path)

    if newly:
        try:
            voiced.update(newly)
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump({"paths": sorted(voiced)}, fh, indent=2)
        except Exception:
            pass
    return items
