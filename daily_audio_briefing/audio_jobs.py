"""
audio_jobs — the Tk-free core of the Reading List → Audio and Direct Audio flows.

Pure functions: fetch article text from URLs, clean it for listening (Gemini
via llm_fallback, optional), combine, and synthesize with Kokoro or gTTS.
Used by gui_app.py (dialogs) and mcp_server.py (agents). No Tk, no MCP here.
"""
import datetime
import os
import re
import sys

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
