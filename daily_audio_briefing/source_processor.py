#!/usr/bin/env python3
"""
Unified Source Processor

Routes sources to appropriate processors based on their type.
Supports: youtube, newsletter, rss (future)

This module provides a unified interface for processing different source types,
each with their own extraction logic and optional config-based filtering.

Usage:
    from source_processor import process_sources

    results = process_sources(
        sources=sources_list,
        target_date=datetime.now(),
        model=gemini_model,
        custom_instructions="..."
    )
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse


def get_resource_path(filename):
    """Get the path to a bundled resource file."""
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def get_data_directory():
    """Get the persistent data directory for user files."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
        elif sys.platform == "win32":
            data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
        else:
            data_dir = os.path.expanduser("~/.daily-audio-briefing")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    else:
        return os.path.dirname(os.path.abspath(__file__))


def log(msg):
    """Log a debug message."""
    print(f"[DEBUG] {msg}")
    sys.stdout.flush()


def load_sources() -> List[Dict]:
    """Load sources from sources.json with backward compatibility."""
    sources_path = get_resource_path("sources.json")

    if not os.path.exists(sources_path):
        log(f"Warning: sources.json not found at {sources_path}")
        return []

    try:
        with open(sources_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        log(f"Error reading sources.json: {e}")
        return []

    sources = data.get("sources", [])

    # Normalize sources - add type field if missing (backward compatibility)
    normalized = []
    for source in sources:
        if not source.get("enabled", True):
            continue

        url = source.get("url", "")
        source_type = source.get("type")

        # Auto-detect type if not specified
        if not source_type:
            source_type = detect_source_type(url)

        normalized.append({
            "url": url,
            "enabled": True,
            "type": source_type,
            "config": source.get("config"),  # Optional extraction config name
            "name": source.get("name"),  # Optional display name
        })

    return normalized


def detect_source_type(url: str) -> str:
    """Auto-detect source type from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # YouTube detection
        if "youtube.com" in domain or "youtu.be" in domain:
            return "youtube"

        # Known newsletter domains
        newsletter_domains = [
            "execsum.co",
            "beehiiv.com",
            "substack.com",
            "mailchimp.com",
            "buttondown.email",
        ]
        for nl_domain in newsletter_domains:
            if nl_domain in domain:
                return "newsletter"

        # RSS feed detection (common patterns)
        if "/feed" in url or "/rss" in url or url.endswith(".xml"):
            return "rss"

        # Default to newsletter for unknown URLs (can be processed as web content)
        return "newsletter"

    except Exception:
        return "newsletter"


def load_extraction_config(config_name: str) -> Optional[Dict]:
    """Load an extraction config by name from extraction_instructions/."""
    if not config_name:
        return None

    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'extraction_instructions',
        f'{config_name}.json'
    )

    if not os.path.exists(config_path):
        log(f"Warning: Extraction config '{config_name}' not found at {config_path}")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading extraction config '{config_name}': {e}")
        return None


def has_capability(config: Optional[Dict], capability: str) -> bool:
    """
    Check if a config has a specific capability enabled.

    Args:
        config: The extraction config dict (or None)
        capability: One of 'csv_export', 'grid_enrichment', 'research_articles', 'custom_prompts'

    Returns:
        True if the capability is enabled, False otherwise
    """
    if not config:
        return False

    capabilities = config.get("capabilities", {})
    return capabilities.get(capability, False)


def get_enabled_capabilities(config: Optional[Dict]) -> List[str]:
    """
    Get a list of all enabled capabilities for a config.

    Args:
        config: The extraction config dict (or None)

    Returns:
        List of enabled capability names
    """
    if not config:
        return []

    capabilities = config.get("capabilities", {})
    return [cap for cap, enabled in capabilities.items() if enabled]


def process_youtube_source(
    source: Dict,
    model: Any,
    shared_context: List[str],
    target_date: datetime.datetime,
    cutoff_time: Optional[datetime.datetime] = None,
    custom_instructions: str = ""
) -> Tuple[List[str], List[str]]:
    """
    Process a YouTube channel source.

    Returns:
        Tuple of (summaries list, updated shared_context)
    """
    # Import here to avoid circular imports
    from get_youtube_news import process_channel

    url = source.get("url", "")
    config_name = source.get("config")

    # Load extraction config if specified (for future use - filtering YouTube content)
    config = load_extraction_config(config_name) if config_name else None

    # Process using existing YouTube logic
    summaries, updated_context = process_channel(
        channel_url=url,
        model=model,
        shared_context=shared_context,
        cutoff_date=target_date,
        cutoff_time=cutoff_time
    )

    return summaries, updated_context


def process_newsletter_source(
    source: Dict,
    model: Any,
    target_date: datetime.datetime,
    custom_instructions: str = ""
) -> List[str]:
    """
    Process a newsletter source using the execsum processor logic.

    Returns:
        List of summary strings
    """
    # Import here to avoid circular imports
    from execsum_processor import (
        extract_newsletter_content,
        load_config,
        summarize_items_with_ai,
        create_basic_summary,
        load_api_key
    )

    url = source.get("url", "")
    config_name = source.get("config")

    # Load the appropriate extraction config
    if config_name:
        config = load_extraction_config(config_name)
        if not config:
            config = load_config()  # Fall back to default execsum config
    else:
        # Try to auto-detect config based on URL
        config = auto_select_newsletter_config(url)

    log(f"--- Processing Newsletter: {url} ---")
    log(f"  Using config: {config.get('name', 'default')}")

    # Extract content from newsletter
    items, newsletter_date = extract_newsletter_content(url, config)

    if not items:
        log(f"  No relevant items found in newsletter")
        return []

    log(f"  Found {len(items)} items to summarize")

    # Generate summary
    api_key = load_api_key()
    if api_key and model:
        content = summarize_items_with_ai(items, api_key)
    else:
        content = create_basic_summary(items)

    if not content.strip():
        return []

    # Format as a summary entry
    date_str = newsletter_date or target_date.strftime("%B %d, %Y")
    source_name = source.get("name") or extract_source_name(url)

    entry = f"=== {source_name} (Articles) ===\n\n{content}"

    return [entry]


def auto_select_newsletter_config(url: str) -> Dict:
    """Auto-select the best extraction config based on URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Map domains to configs
        domain_config_map = {
            "execsum.co": "execsum",
            # Add more mappings as users create configs
        }

        for pattern, config_name in domain_config_map.items():
            if pattern in domain:
                config = load_extraction_config(config_name)
                if config:
                    return config

        # Return empty config (permissive) if no match
        return {}

    except Exception:
        return {}


def extract_source_name(url: str) -> str:
    """Extract a readable source name from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        # Capitalize first letter of each part
        parts = domain.split(".")
        if parts:
            return parts[0].title()
        return domain
    except Exception:
        return "Newsletter"


def process_sources(
    sources: Optional[List[Dict]] = None,
    target_date: Optional[datetime.datetime] = None,
    cutoff_time: Optional[datetime.datetime] = None,
    model: Any = None,
    custom_instructions: str = ""
) -> Dict[str, List[str]]:
    """
    Process all sources and return summaries organized by type.

    Args:
        sources: List of source dicts. If None, loads from sources.json
        target_date: Target date for filtering content
        cutoff_time: Optional cutoff time for hours-based filtering
        model: Gemini model instance for summarization
        custom_instructions: User's custom instructions for summarization

    Returns:
        Dict with keys 'youtube', 'newsletter', etc., each containing list of summaries
    """
    if sources is None:
        sources = load_sources()

    if target_date is None:
        target_date = datetime.datetime.now()

    results = {
        "youtube": [],
        "newsletter": [],
        "rss": [],
    }

    shared_context = []  # Shared across YouTube sources for deduplication

    # Group sources by type
    youtube_sources = [s for s in sources if s.get("type") == "youtube"]
    newsletter_sources = [s for s in sources if s.get("type") == "newsletter"]
    rss_sources = [s for s in sources if s.get("type") == "rss"]

    # Process YouTube sources
    for source in youtube_sources:
        try:
            summaries, shared_context = process_youtube_source(
                source=source,
                model=model,
                shared_context=shared_context,
                target_date=target_date,
                cutoff_time=cutoff_time,
                custom_instructions=custom_instructions
            )
            results["youtube"].extend(summaries)
        except Exception as e:
            log(f"Error processing YouTube source {source.get('url')}: {e}")

    # Process newsletter sources
    for source in newsletter_sources:
        try:
            summaries = process_newsletter_source(
                source=source,
                model=model,
                target_date=target_date,
                custom_instructions=custom_instructions
            )
            results["newsletter"].extend(summaries)
        except Exception as e:
            log(f"Error processing newsletter source {source.get('url')}: {e}")

    # Process RSS sources (future implementation)
    for source in rss_sources:
        log(f"RSS processing not yet implemented: {source.get('url')}")

    return results


def get_all_summaries(results: Dict[str, List[str]]) -> List[str]:
    """Flatten results dict into a single list of summaries."""
    all_summaries = []

    # YouTube first
    all_summaries.extend(results.get("youtube", []))

    # Then newsletters
    all_summaries.extend(results.get("newsletter", []))

    # Then RSS
    all_summaries.extend(results.get("rss", []))

    return all_summaries


if __name__ == "__main__":
    # Test the source processor
    import argparse

    parser = argparse.ArgumentParser(description='Test source processor')
    parser.add_argument('--list', action='store_true', help='List all sources')
    parser.add_argument('--detect', type=str, help='Detect type for a URL')
    args = parser.parse_args()

    if args.list:
        sources = load_sources()
        print(f"\nLoaded {len(sources)} sources:\n")
        for i, s in enumerate(sources, 1):
            print(f"  {i}. [{s['type']}] {s['url']}")
            if s.get('config'):
                print(f"      config: {s['config']}")
        print()

    elif args.detect:
        source_type = detect_source_type(args.detect)
        print(f"\nURL: {args.detect}")
        print(f"Detected type: {source_type}\n")

    else:
        parser.print_help()
