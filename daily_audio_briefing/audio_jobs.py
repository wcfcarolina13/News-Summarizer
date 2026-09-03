"""
audio_jobs — the Tk-free core of the Reading List → Audio and Direct Audio flows.

Pure functions: fetch article text from URLs, clean it for listening (Gemini
via llm_fallback, optional), combine, and synthesize with Kokoro or gTTS.
Used by gui_app.py (dialogs) and mcp_server.py (agents). No Tk, no MCP here.
"""
import datetime
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from llm_fallback import generate_with_fallback
from source_fetcher import _clean_title_for_audio
from file_manager import FileManager, get_data_directory

KOKORO_VOICES = [
    "af_heart", "af_sarah", "af_nova", "af_sky", "af_bella",
    "am_adam", "am_michael", "am_echo",
    "bf_emma", "bf_isabella",
    "bm_george", "bm_lewis",
]
DEFAULT_VOICE = "af_sarah"
READING_LIST_SUBDIR = "Reading List"
QUALITIES = ("quality", "fast")

_STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'this', 'that', 'these',
    'those', 'it', 'its', 'they', 'their', 'we', 'our', 'you', 'your',
    'he', 'she', 'him', 'her', 'his', 'i', 'my', 'me', 'what', 'which',
    'who', 'how', 'when', 'where', 'why', 'all', 'each', 'every', 'both',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
    'new', 'says', 'said', 'according', 'report', 'reports', 'today'
}


def _date_str(now=None):
    return (now or datetime.datetime.now()).strftime("%Y-%m-%d")


def generate_audio_filename(text, extension="wav", now=None):
    """'2026-09-03_bitcoin-etf-approval.wav' from the text's first line/sentence.

    Moved verbatim from gui_app.generate_audio_filename.
    """
    date_str = _date_str(now)
    if not text or len(text.strip()) < 10:
        return f"{date_str}_audio.{extension}"

    lines = text.strip().split('\n')
    first_line = lines[0].strip() if lines else ""
    if first_line and len(first_line) < 100 and not first_line.endswith('.'):
        topic_source = first_line
    else:
        sentences = re.split(r'[.!?]', text[:500])
        topic_source = sentences[0] if sentences else text[:100]

    words = re.findall(r'\b[a-zA-Z]{3,}\b', topic_source.lower())
    key_words = [w for w in words if w not in _STOP_WORDS][:5]
    if not key_words:
        key_words = words[:3] if words else ['audio']

    topic_slug = '-'.join(key_words[:4])
    topic_slug = re.sub(r'[^a-z0-9\-]', '', topic_slug)
    topic_slug = re.sub(r'-+', '-', topic_slug).strip('-')
    if len(topic_slug) > 40:
        topic_slug = topic_slug[:40].rsplit('-', 1)[0]
    if not topic_slug:
        topic_slug = "audio"
    return f"{date_str}_{topic_slug}.{extension}"


def reading_list_basename(titles, now=None):
    """'2026-09-03_reading-list_<slug>_<slug>_<slug>' from up to three titles.

    Moved from gui_app._process_reading_list_inner step 4.
    """
    slugs = []
    for title in titles[:3]:
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:30].strip('-')
        if slug:
            slugs.append(slug)
    slug_part = "_".join(slugs) if slugs else "reading-list"
    if len(slug_part) > 80:
        slug_part = slug_part[:80].rsplit('-', 1)[0]
    return f"{_date_str(now)}_reading-list_{slug_part}"


_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
       'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
FETCH_TIMEOUT = 30
MIN_PARAGRAPH_CHARS = 50
MIN_ARTICLE_CHARS = 100


class CancelledError(Exception):
    """Raised by pipeline steps when cancel() returns True."""


def _check_cancel(cancel):
    if cancel and cancel():
        raise CancelledError()


def _say(progress, msg):
    if progress:
        progress(msg)


def strip_utm(url):
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def _extract_article(html):
    """(title, content) using the reading-list dialog's rules."""
    soup = BeautifulSoup(html, 'html.parser')
    title = ""
    title_elem = soup.find('title') or soup.find('h1')
    if title_elem:
        title = title_elem.get_text(strip=True)
    for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
        elem.decompose()
    main_elem = (
        soup.find('article') or soup.find('main') or
        soup.find(class_=re.compile(r'content|article|post', re.I)) or
        soup.find('body')
    )
    content = ""
    if main_elem:
        paragraphs = main_elem.find_all('p')
        content = '\n\n'.join(
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > MIN_PARAGRAPH_CHARS
        )
    return title, content


def fetch_articles(urls, *, progress=None, cancel=None):
    """Fetch each URL and extract listenable body text.

    Returns one dict per URL, in order: {url, title, content, error}.
    A failed or too-short fetch keeps its slot with content "" and an error
    message, so callers can report exactly what was skipped.
    """
    articles = []
    total = len(urls)
    for i, raw_url in enumerate(urls):
        _check_cancel(cancel)
        url = strip_utm(raw_url.strip())
        _say(progress, f"[1/5] Fetching article {i + 1}/{total}...")
        rec = {"url": url, "title": url, "content": "", "error": None}
        try:
            resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={'User-Agent': _UA})
            resp.raise_for_status()
            title, content = _extract_article(resp.text)
            if title:
                rec["title"] = title
            if content and len(content.strip()) > MIN_ARTICLE_CHARS:
                rec["content"] = content
            else:
                rec["error"] = "too short or empty after extraction"
        except Exception as e:  # network, HTTP, parse — all recorded
            rec["error"] = str(e)
        articles.append(rec)
    return articles


CLEAN_BASE_PROMPT = """Clean and format this text for audio listening. Your task:

1. EXTRACT only the main article/content body
2. REMOVE all of the following:
   - URLs, links, and email addresses
   - Asterisks (*), bullet point markers, markdown formatting
   - "Subscribe", "Click here", "Read more", "Share", "Follow us" and similar CTAs
   - Author bios, bylines, and "About the author" sections
   - "Related articles", "You might also like" sections
   - Advertisements and promotional content
   - Social media handles and hashtags
   - Navigation elements, headers/footers
   - Image captions and alt text descriptions
   - Any text that wouldn't make sense when read aloud

3. PRESERVE the original wording and structure of the actual content
4. FORMAT for natural speech:
   - Expand common abbreviations (e.g., "approx." → "approximately")
   - Keep paragraph breaks for natural pauses
   - Ensure sentences flow naturally when spoken"""

DEFAULT_CLEAN_MODEL = "gemini-2.5-flash"


def build_clean_prompt(text, instructions=""):
    """The Direct Audio / Reading List cleaning prompt (moved from gui_app._clean_single_article)."""
    if instructions:
        head = f"{CLEAN_BASE_PROMPT}\n\n5. ADDITIONAL USER PREFERENCES:\n{instructions}"
    else:
        head = CLEAN_BASE_PROMPT
    return f'{head}\n\nReturn ONLY the cleaned text, nothing else.\n\nTEXT TO CLEAN:\n"""\n{text}\n"""\n'


def _configure_gemini(api_key, model_name):
    """Return a configured google.generativeai model, or None if the SDK is missing."""
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def clean_text(text, *, api_key, instructions="", model_name=DEFAULT_CLEAN_MODEL, progress=None):
    """Clean text for listening. Never raises: on any failure the input is returned."""
    if not api_key:
        _say(progress, "[2/5] No Gemini API key — skipping cleaning, using raw text.")
        return text
    try:
        model = _configure_gemini(api_key, model_name)
        cleaned = generate_with_fallback(build_clean_prompt(text, instructions),
                                         gemini_model=model, caller="audio_jobs.clean_text")
        if cleaned and cleaned.strip():
            return cleaned.strip()
        _say(progress, "[2/5] All LLM providers failed — using raw text.")
        return text
    except Exception as e:
        _say(progress, f"[2/5] Cleaning failed ({e}) — using raw text.")
        return text


def combine_articles(articles):
    """Join cleaned articles with spoken separators, skipping ones with no content."""
    parts = []
    kept = [a for a in articles if a.get("cleaned") or a.get("content")]
    for i, a in enumerate(kept):
        body = a.get("cleaned") or a["content"]
        if i > 0:
            parts.append("\n\nNext article.\n\n")
        parts.append(f"{_clean_title_for_audio(a['title'])}.\n\n")
        parts.append(body)
    return "".join(parts)


def load_article_instructions(data_dir=None):
    """Active profile's article_instructions from instruction_profiles.json, comments stripped."""
    data_dir = data_dir or get_data_directory()
    path = os.path.join(data_dir, "instruction_profiles.json")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""
    active = data.get("active_profile", "Default")
    instructions = data.get("profiles", {}).get(active, {}).get("article_instructions", "") or ""
    lines = [ln for ln in instructions.split("\n") if ln.strip() and not ln.strip().startswith("#")]
    return "\n".join(lines).strip()


def load_gemini_api_key(data_dir=None):
    """.env in the data dir first (FileManager), then GEMINI_API_KEY env var."""
    data_dir = data_dir or get_data_directory()
    key = FileManager(base_dir=data_dir).load_api_key()
    return key or os.environ.get("GEMINI_API_KEY", "")
