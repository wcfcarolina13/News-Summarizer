"""
Source Fetcher Module - Unified content fetching for multiple source types.

Supports:
- YouTube channels (via scrapetube + yt_dlp)
- RSS feeds (via feedparser/BeautifulSoup)
- Article archive pages (link extraction + article fetching)

This module provides a unified interface for the "Get Summaries" feature,
allowing users to fetch content from YouTube, RSS, and article sources
with consistent date filtering and output formatting.
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable, Tuple
from urllib.parse import urlparse

# Debug logging to file
_DEBUG_LOG_FILE = None

def _init_debug_log():
    """Initialize debug log file in the data directory."""
    global _DEBUG_LOG_FILE
    if _DEBUG_LOG_FILE is None:
        try:
            # Try to find the data directory
            if getattr(sys, "frozen", False):
                if sys.platform == "darwin":
                    data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
                elif sys.platform == "win32":
                    data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
                else:
                    data_dir = os.path.expanduser("~/.daily-audio-briefing")
            else:
                data_dir = os.path.dirname(os.path.abspath(__file__))

            os.makedirs(data_dir, exist_ok=True)
            log_path = os.path.join(data_dir, "fetch_debug.log")
            _DEBUG_LOG_FILE = open(log_path, 'w', encoding='utf-8')
            _DEBUG_LOG_FILE.write(f"=== Source Fetcher Debug Log - {datetime.now().isoformat()} ===\n\n")
        except Exception as e:
            _debug_log(f"[SourceFetcher] Could not open debug log: {e}")

def _debug_log(msg: str):
    """Write to both console and debug log file."""
    print(msg)
    global _DEBUG_LOG_FILE
    if _DEBUG_LOG_FILE is None:
        _init_debug_log()
    if _DEBUG_LOG_FILE:
        try:
            _DEBUG_LOG_FILE.write(f"{msg}\n")
            _DEBUG_LOG_FILE.flush()
        except:
            pass

# Optional imports with fallbacks
try:
    import dateparser
    HAS_DATEPARSER = True
except ImportError:
    HAS_DATEPARSER = False
    dateparser = None

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    BeautifulSoup = None


def _parse_date_fallback(date_str: str) -> Optional[datetime]:
    """Fallback date parser when dateparser is not available."""
    if not date_str:
        return None

    # Try common formats
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%a, %d %b %Y %H:%M:%S %z",  # RSS format
        "%a, %d %b %Y %H:%M:%S %Z",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    # Try to handle relative dates like "2 days ago"
    date_lower = date_str.lower().strip()
    now = datetime.now()

    if "ago" in date_lower:
        try:
            parts = date_lower.replace("ago", "").strip().split()
            if len(parts) >= 2:
                num = int(parts[0])
                unit = parts[1]
                if "hour" in unit:
                    return now - timedelta(hours=num)
                elif "day" in unit:
                    return now - timedelta(days=num)
                elif "week" in unit:
                    return now - timedelta(weeks=num)
                elif "month" in unit:
                    return now - timedelta(days=num * 30)
        except (ValueError, IndexError):
            pass

    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string using dateparser or fallback."""
    if HAS_DATEPARSER and dateparser:
        return dateparser.parse(date_str)
    return _parse_date_fallback(date_str)


class SourceType(Enum):
    """Enumeration of supported source types."""
    YOUTUBE = "youtube"
    RSS = "rss"
    ARTICLE_ARCHIVE = "article_archive"
    NEWSLETTER = "newsletter"  # Uses extraction configs for content filtering


@dataclass
class FetchedItem:
    """Represents a fetched content item from any source type."""
    title: str
    url: str
    content: str  # Transcript text or article body
    source_name: str
    source_type: SourceType
    published_date: Optional[datetime] = None
    summary: Optional[str] = None  # AI-generated summary
    metadata: Dict = field(default_factory=dict)


@dataclass
class SourceConfig:
    """Configuration for a content source."""
    url: str
    enabled: bool = True
    source_type: SourceType = SourceType.YOUTUBE
    name: Optional[str] = None  # Display name
    selector: Optional[str] = None  # CSS selector for article archives
    config: Optional[str] = None  # Extraction config name for newsletters (e.g., "execsum")

    @classmethod
    def from_dict(cls, data: dict) -> "SourceConfig":
        """Create SourceConfig from dictionary with automatic type inference."""
        url = data.get("url", "")
        enabled = data.get("enabled", True)
        name = data.get("name")
        selector = data.get("selector")
        config = data.get("config")  # Extraction config name

        # Infer type if not specified
        type_str = data.get("type")
        if type_str:
            try:
                source_type = SourceType(type_str)
            except ValueError:
                source_type = cls._infer_type(url)
        else:
            source_type = cls._infer_type(url)

        return cls(
            url=url,
            enabled=enabled,
            source_type=source_type,
            name=name,
            selector=selector,
            config=config
        )

    @staticmethod
    def _infer_type(url: str) -> SourceType:
        """Infer source type from URL pattern."""
        url_lower = url.lower()

        # YouTube detection
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return SourceType.YOUTUBE

        # RSS/Atom feed detection
        rss_patterns = ['.rss', '.xml', '/feed', '/rss', 'atom', '/feeds/']
        if any(pattern in url_lower for pattern in rss_patterns):
            return SourceType.RSS

        # Default to article archive
        return SourceType.ARTICLE_ARCHIVE

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "url": self.url,
            "enabled": self.enabled,
            "type": self.source_type.value,
        }
        if self.name:
            result["name"] = self.name
        if self.selector:
            result["selector"] = self.selector
        if self.config:
            result["config"] = self.config
        return result


@dataclass
class ArchiveLink:
    """Represents a link found on an article archive page."""
    url: str
    title: str
    date: Optional[datetime] = None
    date_str: Optional[str] = None
    selected: bool = True  # For UI selection


def load_sources(sources_json_path: str, channels_txt_path: str) -> List[SourceConfig]:
    """Load sources from sources.json, with fallback to channels.txt.

    Supports both new format (with type field) and legacy format (YouTube only).
    """
    sources = []

    # Try sources.json first
    if os.path.exists(sources_json_path):
        try:
            with open(sources_json_path, 'r') as f:
                data = json.load(f)

            # Handle both formats: list of sources or dict with "sources" key
            source_list = data if isinstance(data, list) else data.get("sources", [])

            for item in source_list:
                if isinstance(item, dict):
                    sources.append(SourceConfig.from_dict(item))
                elif isinstance(item, str):
                    # Legacy format: just URL strings
                    sources.append(SourceConfig(url=item, source_type=SourceConfig._infer_type(item)))

        except (json.JSONDecodeError, IOError) as e:
            _debug_log(f"[SourceFetcher] Error reading sources.json: {e}")

    # Fallback to channels.txt if no sources loaded
    if not sources and os.path.exists(channels_txt_path):
        try:
            with open(channels_txt_path, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        sources.append(SourceConfig(
                            url=url,
                            enabled=True,
                            source_type=SourceType.YOUTUBE
                        ))
        except IOError as e:
            _debug_log(f"[SourceFetcher] Error reading channels.txt: {e}")

    return sources


def save_sources(sources: List[SourceConfig], sources_json_path: str):
    """Save sources to sources.json."""
    data = {"sources": [s.to_dict() for s in sources]}
    with open(sources_json_path, 'w') as f:
        json.dump(data, f, indent=2)


class SourceFetcher:
    """Unified source fetcher for multiple content types."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """Initialize the fetcher with API credentials.

        Args:
            api_key: Gemini API key for summarization
            model_name: Gemini model to use
        """
        self.api_key = api_key
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy-load the Gemini model."""
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
        return self._model

    def _get_headers(self) -> dict:
        """Get standard HTTP headers for web requests."""
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def fetch_all_sources(
        self,
        sources: List[SourceConfig],
        cutoff_date: datetime,
        max_items_per_source: int = 10,
        progress_callback: Optional[Callable[[str, str], None]] = None,
        youtube_instructions: str = "",
        article_instructions: str = "",
        end_date: Optional[datetime] = None
    ) -> List[FetchedItem]:
        """Fetch content from all enabled sources.

        Args:
            sources: List of source configurations
            cutoff_date: Only fetch items published on or after this date (start date)
            max_items_per_source: Maximum items to fetch per source
            progress_callback: Optional callback(message, color) for progress updates
            youtube_instructions: Custom instructions for YouTube summarization
            article_instructions: Custom instructions for article processing
            end_date: Only fetch items published on or before this date (optional)

        Returns:
            List of FetchedItem objects, sorted by date (newest first)
        """
        all_items = []

        enabled_sources = [s for s in sources if s.enabled]

        # Log source breakdown
        youtube_count = sum(1 for s in enabled_sources if s.source_type == SourceType.YOUTUBE)
        rss_count = sum(1 for s in enabled_sources if s.source_type == SourceType.RSS)
        archive_count = sum(1 for s in enabled_sources if s.source_type == SourceType.ARTICLE_ARCHIVE)
        _debug_log(f"[SourceFetcher] Processing {len(enabled_sources)} sources: {youtube_count} YouTube, {rss_count} RSS, {archive_count} archives")
        _debug_log(f"[SourceFetcher] Date range: {cutoff_date.date()} to {end_date.date() if end_date else 'now'}")

        for i, source in enumerate(enabled_sources):
            _debug_log(f"[SourceFetcher] [{i+1}/{len(enabled_sources)}] Processing: {source.source_type.value} - {source.url[:60]}")

            if progress_callback:
                progress_callback(
                    f"[{i+1}/{len(enabled_sources)}] Fetching: {source.name or source.url[:50]}...",
                    "orange"
                )

            try:
                if source.source_type == SourceType.YOUTUBE:
                    items = self._fetch_youtube(source, cutoff_date, max_items_per_source, youtube_instructions, end_date)
                elif source.source_type == SourceType.RSS:
                    items = self._fetch_rss(source, cutoff_date, max_items_per_source, article_instructions, end_date)
                elif source.source_type == SourceType.NEWSLETTER:
                    items = self._fetch_newsletter(source, cutoff_date, max_items_per_source, end_date)
                elif source.source_type == SourceType.ARTICLE_ARCHIVE:
                    items = self._fetch_article_archive(source, cutoff_date, max_items_per_source, article_instructions)
                else:
                    _debug_log(f"[SourceFetcher] Unknown source type: {source.source_type}")
                    items = []

                _debug_log(f"[SourceFetcher] Got {len(items)} items from {source.url[:40]}")
                all_items.extend(items)

            except Exception as e:
                _debug_log(f"[SourceFetcher] Error fetching {source.url}: {e}")
                import traceback
                traceback.print_exc()
                if progress_callback:
                    progress_callback(f"Error: {source.url[:30]}... - {str(e)[:30]}", "red")

        # Sort by date (newest first)
        all_items.sort(key=lambda x: x.published_date or datetime.min, reverse=True)

        # Final summary
        yt_items = sum(1 for i in all_items if i.source_type == SourceType.YOUTUBE)
        rss_items = sum(1 for i in all_items if i.source_type == SourceType.RSS)
        nl_items = sum(1 for i in all_items if i.source_type == SourceType.NEWSLETTER)
        arc_items = sum(1 for i in all_items if i.source_type == SourceType.ARTICLE_ARCHIVE)
        _debug_log(f"[SourceFetcher] FINAL: {len(all_items)} total items ({yt_items} YouTube, {nl_items} newsletter, {rss_items} RSS, {arc_items} articles)")

        if progress_callback:
            progress_callback(f"Fetched {len(all_items)} items ({yt_items} videos, {nl_items} newsletter, {arc_items} articles)", "green")

        return all_items

    def _fetch_youtube(
        self,
        source: SourceConfig,
        cutoff_date: datetime,
        max_items: int,
        custom_instructions: str,
        end_date: Optional[datetime] = None
    ) -> List[FetchedItem]:
        """Fetch videos from a YouTube channel.

        Uses scrapetube to get video list and yt_dlp for transcripts.
        Filters to only include videos between cutoff_date and end_date (inclusive).
        """
        import scrapetube
        import traceback

        items = []
        _debug_log(f"[YouTube] Fetching channel: {source.url}")
        _debug_log(f"[YouTube] Cutoff date: {cutoff_date.date()}")

        try:
            # Get recent videos from channel
            _debug_log(f"[YouTube] Calling scrapetube.get_channel...")
            video_generator = scrapetube.get_channel(channel_url=source.url, limit=20)
            videos = list(video_generator)
            _debug_log(f"[YouTube] Got {len(videos)} videos from channel")
        except Exception as e:
            _debug_log(f"[YouTube] Error fetching channel {source.url}: {e}")
            traceback.print_exc()
            return []

        if not videos:
            _debug_log(f"[YouTube] No videos returned for {source.url}")
            return []

        # Extract channel name from first video if available
        channel_name = source.name
        if not channel_name and videos:
            try:
                channel_name = videos[0].get("ownerText", {}).get("runs", [{}])[0].get("text", "")
            except:
                channel_name = urlparse(source.url).path.strip("/").split("/")[0]

        _debug_log(f"[YouTube] Channel name: {channel_name}")

        videos_checked = 0
        videos_filtered_by_date = 0
        videos_no_transcript = 0

        for video in videos[:max_items * 2]:  # Fetch extra in case some are filtered
            if len(items) >= max_items:
                break

            videos_checked += 1

            try:
                video_id = video["videoId"]
                title = video["title"]["runs"][0]["text"]

                # Parse publication date
                date_info = video.get("publishedTimeText", {}).get("simpleText", "")
                pub_date = self._parse_youtube_date(date_info)

                _debug_log(f"[YouTube] Video: '{title[:50]}...' date_info='{date_info}' parsed_date={pub_date.date() if pub_date else 'None'}")

                # Filter by date range (start_date <= pub_date <= end_date)
                if pub_date and pub_date.date() < cutoff_date.date():
                    _debug_log(f"[YouTube] Skipping (before start date {cutoff_date.date()}): {title[:40]}...")
                    videos_filtered_by_date += 1
                    continue
                if end_date and pub_date and pub_date.date() > end_date.date():
                    _debug_log(f"[YouTube] Skipping (after end date {end_date.date()}): {title[:40]}...")
                    videos_filtered_by_date += 1
                    continue

                # Get transcript
                _debug_log(f"[YouTube] Fetching transcript for: {video_id}")
                transcript = self._get_youtube_transcript(video_id)
                if not transcript:
                    _debug_log(f"[YouTube] No transcript available for: {title[:40]}...")
                    videos_no_transcript += 1
                    continue

                _debug_log(f"[YouTube] Got transcript ({len(transcript)} chars), summarizing...")

                # Summarize
                summary = self._summarize_youtube(title, transcript, custom_instructions)
                _debug_log(f"[YouTube] Got summary ({len(summary)} chars)")

                items.append(FetchedItem(
                    title=title,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    content=transcript,
                    source_name=channel_name or "YouTube",
                    source_type=SourceType.YOUTUBE,
                    published_date=pub_date,
                    summary=summary,
                    metadata={"video_id": video_id}
                ))

                _debug_log(f"[YouTube] Successfully added: {title[:40]}...")

            except Exception as e:
                _debug_log(f"[YouTube] Error processing video: {e}")
                traceback.print_exc()
                continue

        _debug_log(f"[YouTube] Summary for {source.url}:")
        _debug_log(f"[YouTube]   Videos checked: {videos_checked}")
        _debug_log(f"[YouTube]   Filtered by date: {videos_filtered_by_date}")
        _debug_log(f"[YouTube]   No transcript: {videos_no_transcript}")
        _debug_log(f"[YouTube]   Successfully processed: {len(items)}")

        return items

    def _parse_youtube_date(self, date_str: str) -> Optional[datetime]:
        """Parse YouTube's relative date format."""
        if not date_str:
            return None

        # Clean up YouTube-specific prefixes
        clean_date = date_str
        for prefix in ["Streamed ", "Premiered ", "Scheduled for "]:
            if clean_date.startswith(prefix):
                clean_date = clean_date[len(prefix):]
                break

        return parse_date(clean_date)

    def _get_youtube_transcript(self, video_id: str) -> Optional[str]:
        """Get transcript for a YouTube video using yt_dlp."""
        import yt_dlp
        import glob
        import tempfile

        url = f"https://www.youtube.com/watch?v={video_id}"

        # Use system temp directory for subtitle files
        temp_dir = tempfile.gettempdir()
        temp_prefix = os.path.join(temp_dir, f"dab_sub_{video_id}")

        # Clean up any existing temp files
        for f in glob.glob(f"{temp_prefix}*"):
            try:
                os.remove(f)
            except:
                pass

        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "outtmpl": temp_prefix,
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the subtitle file
            sub_files = glob.glob(f"{temp_prefix}*.vtt") + glob.glob(f"{temp_prefix}*.srt")
            if not sub_files:
                _debug_log(f"[YouTube] No subtitle files found for {video_id}")
                return None

            _debug_log(f"[YouTube] Found subtitle file: {sub_files[0]}")
            with open(sub_files[0], 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean VTT format
            transcript = self._clean_vtt(content)
            _debug_log(f"[YouTube] Cleaned transcript: {len(transcript)} chars")

            # Clean up temp files
            for f in glob.glob(f"{temp_prefix}*"):
                try:
                    os.remove(f)
                except:
                    pass

            return transcript

        except Exception as e:
            _debug_log(f"[YouTube] Transcript error for {video_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _clean_vtt(self, text: str) -> str:
        """Clean VTT subtitle format to plain text."""
        lines = text.splitlines()
        cleaned = []
        last_line = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            if line.startswith("WEBVTT"):
                continue
            if line.startswith("Kind:"):
                continue
            if line.startswith("Language:"):
                continue
            if line == last_line:
                continue

            # Remove HTML tags
            if "<" in line and ">" in line:
                line = re.sub(r"<[^>]+>", "", line)

            cleaned.append(line)
            last_line = line

        return " ".join(cleaned)

    def _summarize_youtube(self, title: str, transcript: str, custom_instructions: str) -> str:
        """Summarize a YouTube transcript using Gemini."""
        try:
            model = self._get_model()

            base_prompt = f"""Summarize this YouTube video transcript for an audio news briefing.

Video Title: {title}

CRITICAL FORMAT REQUIREMENTS - THIS WILL BE READ ALOUD BY TEXT-TO-SPEECH:

1. START DIRECTLY WITH THE CONTENT:
   - NO preambles like "Here's a summary..." or "This video discusses..."
   - NO meta-commentary about the format or your task
   - Just begin with the actual information immediately

2. ABSOLUTELY NO MARKDOWN OR SPECIAL CHARACTERS:
   - NO asterisks (*) for bold or emphasis
   - NO hash symbols (#) for headers
   - NO hyphens (-) or bullets for lists
   - NO parenthetical section labels like "(Intro)" or "(Transition)"
   - NO "**bold text**" formatting

3. WRITE IN PURE FLOWING PROSE:
   - Use transition words: First, Additionally, Furthermore, Moreover, Next, Finally
   - Connect ideas with natural sentence flow, not lists
   - Write complete paragraphs, not bullet points

4. NUMBERS AND DATES - WRITE THEM OUT:
   - "$103,000" becomes "one hundred three thousand dollars"
   - "35%" becomes "thirty-five percent"
   - "January 17" becomes "January seventeenth"
   - "2026" becomes "twenty twenty-six"

5. Keep it comprehensive but conversational.

Your output goes directly to TTS. Any markdown or preambles will sound wrong when read aloud.
"""

            if custom_instructions:
                prompt = f"{base_prompt}\n\nAdditional preferences:\n{custom_instructions}\n\nTranscript:\n{transcript[:15000]}"
            else:
                prompt = f"{base_prompt}\n\nTranscript:\n{transcript[:15000]}"

            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            _debug_log(f"[YouTube] Summarization error: {e}")
            return transcript[:2000]  # Return truncated transcript as fallback

    def _summarize_article(self, title: str, content: str, custom_instructions: str) -> str:
        """Summarize article content using Gemini.

        Only summarizes if the content is long enough to warrant it.
        Short articles are returned as-is.
        """
        # Don't summarize if content is already short (less than 1500 chars)
        if len(content) < 1500:
            _debug_log(f"[Article] Content short ({len(content)} chars), keeping as-is")
            return content

        try:
            model = self._get_model()

            base_prompt = f"""Summarize this article for an audio news briefing.

Article Title: {title}

CRITICAL FORMAT REQUIREMENTS - THIS WILL BE READ ALOUD BY TEXT-TO-SPEECH:

1. START DIRECTLY WITH THE CONTENT:
   - NO preambles like "Here's a summary..." or "This article discusses..."
   - NO meta-commentary about the format or your task
   - Just begin with the actual information immediately

2. ABSOLUTELY NO MARKDOWN OR SPECIAL CHARACTERS:
   - NO asterisks (*) for bold or emphasis
   - NO hash symbols (#) for headers
   - NO hyphens (-) or bullets for lists
   - NO parenthetical section labels like "(Intro)" or "(Transition)"
   - NO "**bold text**" formatting

3. WRITE IN PURE FLOWING PROSE:
   - Use transition words: First, Additionally, Furthermore, Moreover, Next, Finally
   - Connect ideas with natural sentence flow, not lists
   - Write complete paragraphs, not bullet points

4. NUMBERS AND DATES - WRITE THEM OUT:
   - "$103,000" becomes "one hundred three thousand dollars"
   - "35%" becomes "thirty-five percent"
   - "January 17" becomes "January seventeenth"
   - "2026" becomes "twenty twenty-six"

5. Keep it concise (two to four paragraphs) but comprehensive and conversational.

Your output goes directly to TTS. Any markdown or preambles will sound wrong when read aloud.
"""

            if custom_instructions:
                prompt = f"{base_prompt}\n\nAdditional preferences:\n{custom_instructions}\n\nArticle Content:\n{content[:15000]}"
            else:
                prompt = f"{base_prompt}\n\nArticle Content:\n{content[:15000]}"

            response = model.generate_content(prompt)
            summary = response.text
            _debug_log(f"[Article] Summarized {len(content)} chars to {len(summary)} chars")
            return summary

        except Exception as e:
            _debug_log(f"[Article] Summarization error: {e}")
            # Return first portion of content as fallback
            return content[:2000] + "..." if len(content) > 2000 else content

    def summarize_article_content(self, title: str, content: str, custom_instructions: str = "") -> str:
        """Public method to summarize article content.

        Used by the GUI when processing selected articles from archives.
        """
        return self._summarize_article(title, content, custom_instructions)

    def _fetch_rss(
        self,
        source: SourceConfig,
        cutoff_date: datetime,
        max_items: int,
        custom_instructions: str,
        end_date: Optional[datetime] = None
    ) -> List[FetchedItem]:
        """Fetch items from an RSS feed.

        Filters to only include items between cutoff_date and end_date (inclusive).
        """
        if not HAS_REQUESTS or not HAS_BS4:
            print("[RSS] Missing required libraries: requests or beautifulsoup4")
            return []

        items = []

        try:
            response = requests.get(source.url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; DailyAudioBriefing/1.0)'
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')

            # Get feed title
            feed_title = soup.find('title')
            source_name = source.name or (feed_title.get_text(strip=True) if feed_title else urlparse(source.url).netloc)

            # Handle both RSS and Atom formats
            entries = soup.find_all('item') or soup.find_all('entry')

            for entry in entries[:max_items * 2]:
                if len(items) >= max_items:
                    break

                try:
                    title_elem = entry.find('title')
                    link_elem = entry.find('link')
                    desc_elem = entry.find('description') or entry.find('summary') or entry.find('content')
                    date_elem = entry.find('pubDate') or entry.find('published') or entry.find('updated')

                    # Get link URL
                    if link_elem:
                        link_url = link_elem.get('href') or link_elem.get_text(strip=True)
                    else:
                        continue

                    # Parse date
                    pub_date = None
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        pub_date = parse_date(date_str)

                    # Filter by date range (start_date <= pub_date <= end_date)
                    if pub_date and pub_date.date() < cutoff_date.date():
                        continue
                    if end_date and pub_date and pub_date.date() > end_date.date():
                        continue

                    # Get description/content
                    content = ""
                    if desc_elem:
                        # Clean HTML from description
                        desc_soup = BeautifulSoup(desc_elem.get_text(), 'html.parser')
                        content = desc_soup.get_text(strip=True)

                    title = title_elem.get_text(strip=True) if title_elem else ""

                    items.append(FetchedItem(
                        title=title,
                        url=link_url,
                        content=content,
                        source_name=source_name,
                        source_type=SourceType.RSS,
                        published_date=pub_date,
                        summary=content[:500] if content else None  # Use description as summary
                    ))

                except Exception as e:
                    _debug_log(f"[RSS] Error parsing entry: {e}")
                    continue

        except Exception as e:
            _debug_log(f"[RSS] Error fetching {source.url}: {e}")

        return items

    def _fetch_newsletter(
        self,
        source: SourceConfig,
        cutoff_date: datetime,
        max_items: int,
        end_date: Optional[datetime] = None
    ) -> List[FetchedItem]:
        """Fetch content from a newsletter using extraction config for filtering.

        For newsletters, we extract the ACTUAL CONTENT (article text, headlines)
        rather than extracting links. This is different from how DataCSVProcessor
        works for CSV export - here we want the readable content for TTS.

        Note: max_items controls how many POSTS to process, not headlines.
        Each post may contain many headlines. For a 2-day date range, typically
        want 2-4 posts max.
        """
        _debug_log(f"[Newsletter] Fetching: {source.url}")
        _debug_log(f"[Newsletter] Config: {source.config}")
        _debug_log(f"[Newsletter] Date range: {cutoff_date.date()} to {end_date.date() if end_date else 'now'}")

        items = []

        # Calculate how many posts to fetch based on date range
        # ExecSum publishes ~1-2 posts per weekday
        if end_date:
            days_in_range = (end_date.date() - cutoff_date.date()).days + 1
            # Estimate 2 posts per day, but cap at max_items
            posts_to_fetch = min(days_in_range * 2, max_items)
        else:
            posts_to_fetch = max_items

        _debug_log(f"[Newsletter] Will process up to {posts_to_fetch} posts")

        try:
            # Load the extraction config if specified
            config_dict = {}
            if source.config:
                config_path = self._get_config_path(source.config)
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_dict = json.load(f)
                    _debug_log(f"[Newsletter] Loaded config from {config_path}")
                else:
                    _debug_log(f"[Newsletter] Config file not found: {config_path}")

            # Check if this is a listing page (archive) or a direct post
            url_lower = source.url.lower()
            is_listing_page = '/authors' in url_lower or '/archive' in url_lower

            if is_listing_page:
                # Fetch the listing page and extract links to actual posts
                _debug_log(f"[Newsletter] Detected listing page, extracting post links...")
                post_urls = self._extract_newsletter_post_links(source.url, config_dict)
                _debug_log(f"[Newsletter] Found {len(post_urls)} post links")

                # Process each post URL (limited by posts_to_fetch)
                for post_url in post_urls[:posts_to_fetch]:
                    _debug_log(f"[Newsletter] Processing post: {post_url[:60]}...")
                    try:
                        post_items = self._extract_newsletter_content(post_url, source, config_dict)
                        items.extend(post_items)
                    except Exception as e:
                        _debug_log(f"[Newsletter] Error processing post {post_url}: {e}")
            else:
                # Direct post URL - extract content directly
                _debug_log(f"[Newsletter] Processing direct post URL...")
                items = self._extract_newsletter_content(source.url, source, config_dict)

            _debug_log(f"[Newsletter] Created {len(items)} FetchedItems total")

        except Exception as e:
            _debug_log(f"[Newsletter] Error processing {source.url}: {e}")
            import traceback
            traceback.print_exc()

        return items

    def _get_config_path(self, config_name: str) -> str:
        """Get the full path to an extraction config file."""
        # Try frozen app path first
        if getattr(sys, 'frozen', False):
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        return os.path.join(base_path, 'extraction_instructions', f'{config_name}.json')

    def _extract_newsletter_content(
        self,
        url: str,
        source: SourceConfig,
        config_dict: dict
    ) -> List[FetchedItem]:
        """Extract headlines from a newsletter post page.

        This method extracts clean headline text for TTS output.
        It deduplicates content and applies the extraction config filters.
        """
        items = []
        seen_headlines = set()  # For deduplication

        try:
            # Fetch the page
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Get source name
            source_name = source.name or config_dict.get('name', 'Newsletter')

            # Remove unwanted elements completely
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe', 'header', 'aside']):
                tag.decompose()

            # Find the main content area (post-content for beehiiv)
            content_area = (
                soup.find('div', class_='post-content') or
                soup.find('article') or
                soup.find('main') or
                soup.body
            )

            if not content_area:
                _debug_log(f"[Newsletter] No content area found in {url[:50]}")
                return items

            # Get filters from config
            include_patterns = config_dict.get('include_patterns', [])
            exclude_patterns = config_dict.get('exclude_patterns', [])
            exclude_sections = config_dict.get('exclude_sections', [])
            allowed_source_domains = config_dict.get('allowed_source_domains', [])
            require_include = config_dict.get('require_include_pattern', False)

            # Sections where we DON'T require trusted source links (e.g., Markets section has internal data)
            no_source_check_sections = ['markets']

            # Track which section we're in
            current_section = "General"
            in_excluded_section = False

            # ExecSum newsletters have headlines as <p> tags with <a> links inside
            # The structure is: <p><a href="...">Headline text with context</a></p>
            # For quality filtering, we prefer items that link to trusted sources (BBG, RT, FT, etc.)
            # EXCEPT for special sections like "Markets" which have valuable internal data
            #
            # NOTE: The Markets section uses bullet points (<li> in <ul>), not <p> tags!
            # So we need to include 'li' in our search, but be careful to only capture
            # list items in the Markets section (or other approved sections).

            for element in content_area.find_all(['h2', 'h3', 'p', 'li']):
                # Check for section headers (h2, h3)
                if element.name in ['h2', 'h3']:
                    header_text = element.get_text(strip=True)
                    if header_text:
                        _debug_log(f"[Newsletter] Found section header: '{header_text}' (tag: {element.name})")
                        # Check if this is an excluded section
                        in_excluded_section = any(
                            exc.lower() in header_text.lower()
                            for exc in exclude_sections
                        )
                        if not in_excluded_section:
                            current_section = header_text
                            _debug_log(f"[Newsletter] Set current_section to: '{current_section}'")
                    continue

                # Also check for "Markets" in <p> tags with <strong> - ExecSum uses this format
                # The structure is: <p><strong>Markets</strong></p> followed by <ul><li>...</li></ul>
                if element.name == 'p':
                    strong = element.find('strong')
                    if strong:
                        strong_text = strong.get_text(strip=True)
                        # Check if this is a section header (short text, likely bold section name)
                        if strong_text and len(strong_text) < 30 and strong_text.lower() in ['markets', 'headline roundup', 'deal flow']:
                            _debug_log(f"[Newsletter] Found section header in <strong>: '{strong_text}'")
                            in_excluded_section = any(
                                exc.lower() in strong_text.lower()
                                for exc in exclude_sections
                            )
                            if not in_excluded_section:
                                current_section = strong_text
                                _debug_log(f"[Newsletter] Set current_section to: '{current_section}'")
                            continue

                # Skip if in excluded section
                if in_excluded_section:
                    continue

                # Get the text content - use separator=' ' to preserve spacing between elements
                text = element.get_text(separator=' ', strip=True)
                # Clean up multiple spaces
                text = ' '.join(text.split())

                # Check if we're in a section that doesn't require source checking (e.g., Markets)
                in_no_source_check_section = current_section.lower() in no_source_check_sections

                # For <li> elements, ONLY capture them in special sections like Markets
                # Otherwise we'll pick up all the Deal Flow noise which uses bullet points
                if element.name == 'li':
                    if not in_no_source_check_section:
                        _debug_log(f"[Newsletter] Skipping li (not in markets): section='{current_section}', text='{text[:50]}...'")
                        continue
                    else:
                        _debug_log(f"[Newsletter] Including li from Markets section: '{text[:50]}...'")

                # Skip empty or very short content
                if not text or len(text) < 30:
                    continue

                # Skip if it looks like navigation or UI
                if self._is_navigation_text(text):
                    continue

                # Check if this element has a link to a trusted source
                # This is key for quality filtering - we want BBG, RT, FT, CNBC links
                link = element.find('a', href=True)
                link_href = link.get('href', '') if link else ''

                # Check if link is from a trusted/allowed source domain
                has_trusted_source = False
                if link_href and allowed_source_domains:
                    link_lower = link_href.lower()
                    has_trusted_source = any(domain in link_lower for domain in allowed_source_domains)

                # If allowed_source_domains is specified, ONLY include items with trusted sources
                # This filters out the "deal flow" noise that doesn't link to major news sources
                # EXCEPT for special sections like "Markets" which have valuable internal data
                if allowed_source_domains and not has_trusted_source and not in_no_source_check_section:
                    continue

                # Normalize text for deduplication (lowercase, strip extra whitespace)
                text_normalized = ' '.join(text.lower().split())

                # Skip if we've already seen this headline (deduplication)
                if text_normalized in seen_headlines:
                    continue

                # Check for substring matches (one headline contained in another)
                is_substring = False
                for seen in seen_headlines:
                    if text_normalized in seen or seen in text_normalized:
                        is_substring = True
                        break
                if is_substring:
                    continue

                # Apply exclude patterns
                if any(pat.lower() in text.lower() for pat in exclude_patterns):
                    _debug_log(f"[Newsletter] Excluded by pattern: {text[:50]}...")
                    continue

                # Apply include patterns (if require_include_pattern is True)
                if require_include and include_patterns:
                    if not any(pat.lower() in text.lower() for pat in include_patterns):
                        continue

                # This is a valid headline - add it
                seen_headlines.add(text_normalized)

                items.append(FetchedItem(
                    title=text,
                    url=url,
                    content=text,
                    source_name=source_name,
                    source_type=SourceType.NEWSLETTER,
                    published_date=datetime.now(),
                    summary=text,  # Clean headline text, no prefix
                    metadata={"section": current_section, "config": source.config}
                ))

            _debug_log(f"[Newsletter] Extracted {len(items)} unique headlines from {url[:50]}")

        except Exception as e:
            _debug_log(f"[Newsletter] Error extracting content from {url}: {e}")
            import traceback
            traceback.print_exc()

        return items

    def _is_navigation_text(self, text: str) -> bool:
        """Check if text looks like navigation/UI element or promotional content."""
        text_lower = text.lower().strip()

        # Single word nav items
        nav_words = [
            'login', 'signup', 'subscribe', 'menu', 'home', 'about',
            'contact', 'faq', 'terms', 'privacy', 'merch', 'store',
            'consulting', 'identifier', '404', 'user', 'share',
            'tweet', 'follow', 'like', 'comment', 'reply',
            'read more', 'see more', 'view all', 'load more',
            'next', 'previous', 'back', 'forward', 'litquidity',
            'exec sum', 'exec.sum', 'execsum'
        ]

        if text_lower in nav_words:
            return True

        # Very short single-word text
        if len(text) < 15 and ' ' not in text:
            return True

        # Promotional/marketing phrases
        promo_phrases = [
            'message from', 'a message from', 'sponsored by', 'presented by',
            'brought to you', 'use code', 'discount', 'off any order',
            'shop now', 'buy now', 'click here', 'learn more',
            'sign up', 'join now', 'get started', 'free trial',
            'daily newsletter', 'curates major news', 'read by',
            'investment bankers', 'institutional investors', 'venture capitalists',
            'touch of memes', 'silicon valley', 'wall street to',
            'the new year means', 'wardrobe overhaul', 'don\'t stress',
            'machine washable', 'performance fabric', 'wrinkle resistant',
            'i legit love', 'stop sacrificing', 'comfort for style',
            # OLarry tax service ads
            'olarry', 'tax advisory', 'flat fee', 'flat price', 'book a free consultation',
            'proactive, year-round', 'outgrown \'tax prep\'', 'zero cross-selling',
            'proven track record', 'unlimited strategy', 'pass-through complexity',
            'chasing down your cpa', 'go beyond traditional tax',
            # Wharton/course ads
            'enroll and save', 'lifetime access to networking', 'globally recognized certificate',
            'running the model and running the deal', 'wharton online',
            # Earnings calendar
            'what we\'re watching this week', 'earnings calendar',
        ]

        for phrase in promo_phrases:
            if phrase in text_lower:
                return True

        # Section header patterns (these are categories, not news headlines)
        section_headers = [
            'bankruptcy / restructuring',
            'ipo / direct listings',
            'ipos / direct listings',
            'fundraising / secondaries',
            'deal flow',
            'headline roundup',
            'ipo / direct listings / issuances / block trades',
        ]

        for header in section_headers:
            if text_lower == header or text_lower.startswith(header):
                return True

        return False

    def _is_internal_link(self, href: str, source_url: str) -> bool:
        """Check if link is internal navigation."""
        href_lower = href.lower()

        internal_patterns = [
            '/subscribe', '/login', '/signup', '/share', '/auth',
            'twitter.com/intent', 'facebook.com/sharer', 'linkedin.com/share',
            'mailto:', '#', 'javascript:'
        ]

        return any(pattern in href_lower for pattern in internal_patterns)

    def _extract_newsletter_post_links(self, listing_url: str, config_dict: dict) -> List[str]:
        """Extract links to newsletter posts from a listing/archive page.

        Filters for actual post URLs (like /p/) and excludes navigation links.
        """
        post_urls = []

        try:
            response = requests.get(listing_url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Get the base domain for filtering
            from urllib.parse import urlparse, urljoin
            parsed = urlparse(listing_url)
            base_domain = parsed.netloc

            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Make absolute URL
                full_url = urljoin(listing_url, href)
                parsed_link = urlparse(full_url)

                # Only include links from the same domain
                if base_domain not in parsed_link.netloc:
                    continue

                # Filter for post URLs (common patterns)
                path_lower = parsed_link.path.lower()

                # ExecSum and beehiiv use /p/ for posts
                # Substack uses similar patterns
                if '/p/' in path_lower:
                    if full_url not in post_urls:
                        post_urls.append(full_url)
                        _debug_log(f"[Newsletter] Found post: {full_url[:60]}...")

            # NOTE: We do NOT filter by blocked_domains here because those are meant
            # for filtering external links in content, not the newsletter posts themselves.
            # The execsum.json config blocks execsum.co to avoid self-referential links
            # in article extraction, but we want the actual /p/ posts.

        except Exception as e:
            _debug_log(f"[Newsletter] Error extracting post links: {e}")

        return post_urls

    def _fetch_article_archive(
        self,
        source: SourceConfig,
        cutoff_date: datetime,
        max_items: int,
        custom_instructions: str
    ) -> List[FetchedItem]:
        """Fetch articles from an archive/author page.

        This extracts article links from the page for later selection.
        """
        # For article archives, we return empty here - the actual fetching
        # happens through the GUI selector dialog
        # This method just validates the source can be accessed
        return []

    def extract_archive_links(
        self,
        url: str,
        selector: Optional[str] = None
    ) -> List[ArchiveLink]:
        """Extract article links from an archive page.

        Used by the GUI to show a selection dialog.

        Args:
            url: The archive page URL
            selector: Optional CSS selector to find article links

        Returns:
            List of ArchiveLink objects for user selection
        """
        if not HAS_REQUESTS or not HAS_BS4:
            print("[Archive] Missing required libraries: requests or beautifulsoup4")
            return []

        links = []

        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try custom selector first
            if selector:
                elements = soup.select(selector)
            else:
                # Common patterns for article links
                elements = []

                # Look for article elements
                for article in soup.find_all(['article', 'div'], class_=re.compile(r'post|article|entry|item', re.I)):
                    link = article.find('a', href=True)
                    if link:
                        elements.append(link)

                # If no articles found, look for links with article-like paths
                if not elements:
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        # Common article URL patterns
                        if re.search(r'/p/|/posts?/|/articles?/|/\d{4}/\d{2}/', href):
                            elements.append(link)

            # Extract link info
            seen_urls = set()
            for elem in elements:
                href = elem.get('href', '')
                if not href or href in seen_urls:
                    continue

                # Make absolute URL
                if href.startswith('/'):
                    parsed = urlparse(url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                elif not href.startswith('http'):
                    continue

                seen_urls.add(href)

                # Get title - try multiple strategies for better text
                title = ""

                # Strategy 1: Look for heading elements inside the link
                heading = elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading:
                    title = heading.get_text(strip=True)

                # Strategy 2: Look for an element with class containing 'title'
                if not title:
                    title_elem = elem.find(class_=re.compile(r'title', re.I))
                    if title_elem:
                        title = title_elem.get_text(strip=True)

                # Strategy 3: Check parent/sibling for heading
                if not title and elem.parent:
                    parent = elem.parent
                    heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        title = heading.get_text(strip=True)
                    # Also check for title class in parent
                    if not title:
                        title_elem = parent.find(class_=re.compile(r'title', re.I))
                        if title_elem:
                            title = title_elem.get_text(strip=True)

                # Strategy 4: Use link text but filter out noise
                if not title:
                    raw_text = elem.get_text(strip=True)
                    # Filter out common noise patterns
                    raw_text = re.sub(r'\d+\s*min\s*read', '', raw_text, flags=re.I)
                    raw_text = re.sub(r'•|·|\|', ' ', raw_text)
                    raw_text = ' '.join(raw_text.split())  # Normalize whitespace

                    # If text is too short or looks like metadata, use URL
                    if len(raw_text) > 10 and not re.match(r'^[A-Za-z]{1,20}$', raw_text):
                        title = raw_text
                    else:
                        # Extract from URL path
                        path_parts = [p for p in href.split('/') if p and not p.startswith('?')]
                        if path_parts:
                            last_part = path_parts[-1]
                            # Remove file extensions and query strings
                            last_part = re.sub(r'\.(html?|php|aspx?).*$', '', last_part, flags=re.I)
                            title = last_part.replace('-', ' ').replace('_', ' ').title()

                if not title:
                    title = "(Untitled)"

                # Try to find date near the link
                date = None
                date_str = None
                parent = elem.parent
                if parent:
                    # Look for time elements or date-like text
                    time_elem = parent.find('time')
                    if time_elem:
                        date_str = time_elem.get('datetime') or time_elem.get_text(strip=True)
                        date = parse_date(date_str) if date_str else None
                    # Also check grandparent
                    if not date and parent.parent:
                        time_elem = parent.parent.find('time')
                        if time_elem:
                            date_str = time_elem.get('datetime') or time_elem.get_text(strip=True)
                            date = parse_date(date_str) if date_str else None

                links.append(ArchiveLink(
                    url=href,
                    title=title[:200],
                    date=date,
                    date_str=date_str,
                    selected=True
                ))

        except Exception as e:
            _debug_log(f"[Archive] Error extracting links from {url}: {e}")

        return links

    def fetch_article_content(self, url: str) -> Tuple[str, str]:
        """Fetch and clean article content from a URL.

        Returns:
            Tuple of (title, content)
        """
        if not HAS_REQUESTS or not HAS_BS4:
            print("[Article] Missing required libraries: requests or beautifulsoup4")
            return "", ""

        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get title
            title = ""
            title_elem = soup.find('title') or soup.find('h1')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # Remove unwanted elements
            for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                elem.decompose()

            # Try to find main content
            content = ""
            main_elem = (
                soup.find('article') or
                soup.find('main') or
                soup.find(class_=re.compile(r'content|article|post', re.I)) or
                soup.find('body')
            )

            if main_elem:
                # Get text from paragraphs
                paragraphs = main_elem.find_all('p')
                content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50)

            return title, content

        except Exception as e:
            _debug_log(f"[Article] Error fetching {url}: {e}")
            return "", ""


def _clean_title_for_audio(title: str) -> str:
    """Clean a title for text-to-speech by removing/replacing problematic symbols."""
    import re

    # Replace pipe with dash (reads better)
    title = title.replace(" | ", " - ")
    title = title.replace("|", " - ")

    # Remove or replace other problematic symbols
    title = title.replace(":", "")  # Colons don't read well
    title = title.replace("!!", "!")  # Reduce repeated punctuation
    title = title.replace("??", "?")
    title = title.replace("...", "")

    # Remove emojis (they read as descriptions like "fire emoji")
    title = re.sub(r'[🔥🚀📉📈💥⚡🚨💰🎯✅❌🔴🟢⬆️⬇️]', '', title)

    # Clean up extra whitespace
    title = re.sub(r'\s+', ' ', title).strip()

    return title


def format_items_for_audio(items: List[FetchedItem]) -> str:
    """Format fetched items into text suitable for audio generation (TTS).

    Groups items by source type and formats with spoken-friendly headers.
    No symbols, markdown, or formatting that doesn't translate to speech.
    """
    if not items:
        return ""

    output_parts = []

    # Group by source type first, then by source name
    from collections import defaultdict
    by_type = defaultdict(list)
    for item in items:
        by_type[item.source_type].append(item)

    # Process YouTube videos first
    if SourceType.YOUTUBE in by_type:
        youtube_items = by_type[SourceType.YOUTUBE]
        output_parts.append("\nFrom YouTube videos:\n")

        for item in youtube_items:
            date_str = item.published_date.strftime("%B %d, %Y") if item.published_date else "recent"
            clean_title = _clean_title_for_audio(item.title)

            # Natural spoken intro instead of "Title (Date):"
            output_parts.append(f"\nRegarding the video titled {clean_title}, published {date_str}.\n")

            if item.summary:
                output_parts.append(f"{item.summary}\n")
            elif item.content:
                output_parts.append(f"{item.content}\n")

    # Process articles
    if SourceType.ARTICLE_ARCHIVE in by_type:
        article_items = by_type[SourceType.ARTICLE_ARCHIVE]
        output_parts.append("\nFrom articles:\n")

        for item in article_items:
            date_str = item.published_date.strftime("%B %d, %Y") if item.published_date else "recent"
            clean_title = _clean_title_for_audio(item.title)

            # Clean up source name - extract readable name from URL if needed
            source = item.source_name
            if source and "http" in source:
                # Extract domain and make it readable
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(source).netloc.replace("www.", "")
                    # Map known domains to readable names
                    domain_names = {
                        "execsum.co": "Exec Sum",
                        "bloomberg.com": "Bloomberg",
                        "reuters.com": "Reuters",
                        "wsj.com": "Wall Street Journal",
                        "ft.com": "Financial Times",
                        "cnbc.com": "CNBC",
                    }
                    source = domain_names.get(domain, domain.split('.')[0].title())
                except:
                    source = "the newsletter"
            elif not source:
                source = "the newsletter"

            output_parts.append(f"\nFrom {source}, an article titled {clean_title}, dated {date_str}.\n")

            if item.summary:
                output_parts.append(f"{item.summary}\n")
            elif item.content:
                output_parts.append(f"{item.content}\n")

    # Process newsletter items (headlines extracted with config filters)
    if SourceType.NEWSLETTER in by_type:
        newsletter_items = by_type[SourceType.NEWSLETTER]
        # Group by source name
        by_source = defaultdict(list)
        for item in newsletter_items:
            by_source[item.source_name].append(item)

        for source_name, items_list in by_source.items():
            output_parts.append(f"\nFrom {source_name} Newsletter:\n")

            for item in items_list:
                # Newsletter items are clean headlines - just output them directly
                headline = item.summary or item.content or item.title
                if headline:
                    clean_headline = _clean_title_for_audio(headline)
                    output_parts.append(f"{clean_headline}")

    # Process RSS feeds
    if SourceType.RSS in by_type:
        rss_items = by_type[SourceType.RSS]
        output_parts.append("\nFrom RSS feeds:\n")

        for item in rss_items:
            date_str = item.published_date.strftime("%B %d, %Y") if item.published_date else "recent"
            clean_title = _clean_title_for_audio(item.title)

            output_parts.append(f"\nFrom {item.source_name}, {clean_title}, dated {date_str}.\n")

            if item.summary:
                output_parts.append(f"{item.summary}\n")
            elif item.content:
                output_parts.append(f"{item.content}\n")

    return "\n".join(output_parts)
