#!/usr/bin/env python3
"""
ExecSum Newsletter Processor

Processes ExecSum newsletters, filters content based on trained config,
fetches article summaries, and outputs podcast-style text for audio conversion.

Output goes to the same weekly folder as the news summarizer.

Usage:
    python execsum_processor.py <newsletter_url> [<newsletter_url2> ...]
    python execsum_processor.py --urls-file urls.txt
    python execsum_processor.py https://www.execsum.co/p/merry-christmas-from-ours-to-yours
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Try to import google.generativeai for summarization
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


def get_data_directory():
    """Get the appropriate data directory for storing output files."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            data_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
        elif sys.platform == "win32":
            data_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
        else:
            data_dir = os.path.expanduser("~/.daily-audio-briefing")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        return data_dir
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_week_folder() -> str:
    """Get the current week folder path, creating it if needed."""
    data_dir = get_data_directory()
    now = datetime.now()
    week_num = now.isocalendar()[1]
    year = now.year
    folder_name = f"Week_{week_num}_{year}"
    folder_path = os.path.join(data_dir, folder_name)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    return folder_path


def strip_utm_params(url: str) -> str:
    """Remove UTM and tracking parameters from URL."""
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        tracking_prefixes = ('utm_', 'ref', 'source', 'campaign', 'medium', 'fbclid', 'gclid',
                            'mc_', 'ml_', '_ga', '_gl', 'sref', 'smid', 'unlocked_article_code')
        filtered_params = {k: v for k, v in params.items()
                         if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)}
        new_query = urlencode(filtered_params, doseq=True) if filtered_params else ''
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ''))
    except Exception:
        return url


def load_config() -> Dict:
    """Load the ExecSum extraction config."""
    config_path = os.path.join(os.path.dirname(__file__), 'extraction_instructions', 'execsum.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        return {}


def load_api_key() -> Optional[str]:
    """Load Gemini API key from .env file."""
    env_path = os.path.join(get_data_directory(), '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(__file__), '.env')

    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('GEMINI_API_KEY='):
                        return line.strip().split('=', 1)[1].strip('"\'')
        except Exception:
            pass
    return os.environ.get('GEMINI_API_KEY')


def is_blocked_url(url: str, config: Dict) -> bool:
    """Check if URL should be blocked based on config."""
    blocked_domains = config.get('blocked_domains', [])
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        return any(blocked.lower() in domain for blocked in blocked_domains)
    except Exception:
        return False


def matches_exclude_pattern(text: str, config: Dict) -> bool:
    """Check if text matches exclusion patterns."""
    exclude_patterns = config.get('exclude_patterns', [])
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in exclude_patterns)


def matches_include_pattern(text: str, config: Dict) -> bool:
    """Check if text matches any include pattern (for whitelist filtering)."""
    include_patterns = config.get('include_patterns', [])
    if not include_patterns:
        return True  # No include patterns means include all
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in include_patterns)


def is_in_excluded_section(section: str, config: Dict) -> bool:
    """Check if section is in the excluded sections list."""
    exclude_sections = config.get('exclude_sections', [])
    section_lower = section.lower()
    return any(exc.lower() in section_lower for exc in exclude_sections)


def get_source_name(url: str) -> str:
    """Get readable source name from URL."""
    domain_map = {
        'reuters.com': 'Reuters',
        'bloomberg.com': 'Bloomberg',
        'ft.com': 'Financial Times',
        'cnbc.com': 'CNBC',
        'nytimes.com': 'New York Times',
        'wsj.com': 'Wall Street Journal',
        'economist.com': 'The Economist',
        'awealthofcommonsense.com': 'A Wealth of Common Sense',
    }
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        for key, name in domain_map.items():
            if key in domain:
                return name
        return domain.split('.')[0].title()
    except Exception:
        return 'Unknown'


def get_clean_page_text(soup) -> str:
    """Get page text with proper line breaks between elements."""
    # Get the HTML, replace <br> tags with newlines in the string
    html_str = str(soup)

    # Replace various br tag formats with newlines
    html_str = re.sub(r'<br\s*/?>', '\n', html_str, flags=re.IGNORECASE)

    # Also ensure block elements create line breaks
    for tag in ['</p>', '</div>', '</li>', '</h1>', '</h2>', '</h3>', '</h4>', '</h5>', '</h6>']:
        html_str = html_str.replace(tag, tag + '\n')

    # Parse again and get text
    temp_soup = BeautifulSoup(html_str, 'html.parser')
    page_text = temp_soup.get_text(separator='\n', strip=True)

    # Normalize multiple newlines
    page_text = re.sub(r'\n+', '\n', page_text)

    return page_text


def extract_markets_section(soup, config: Dict) -> List[Dict]:
    """Extract bullet points from the Markets section (no hyperlinks needed)."""
    items = []
    bullet_items = []

    # Get clean page text with proper line breaks
    page_text = get_clean_page_text(soup)

    # Find all Markets sections (there may be multiple per newsletter)
    markets_starts = []
    idx = 0
    while True:
        # Look for *Markets or standalone Markets header
        star_idx = page_text.find('*Markets', idx)
        plain_idx = page_text.find('\nMarkets\n', idx)

        if star_idx == -1 and plain_idx == -1:
            break

        if star_idx != -1 and (plain_idx == -1 or star_idx < plain_idx):
            markets_starts.append(star_idx)
            idx = star_idx + 10
        else:
            markets_starts.append(plain_idx)
            idx = plain_idx + 10

    if not markets_starts:
        return items

    # Section end markers
    section_markers = ['Earnings', 'Prediction Markets', 'Headline Roundup', 'Deal Flow',
                      'Before The Bell', "Exec's Picks", 'Execs Picks', '*Markets']

    for markets_idx in markets_starts:
        # Find where this section ends
        end_idx = len(page_text)
        for marker in section_markers:
            idx = page_text.find(marker, markets_idx + 10)
            if idx != -1 and idx < end_idx:
                end_idx = idx

        markets_text = page_text[markets_idx:end_idx]

        # Split into lines and extract bullet points
        lines = markets_text.split('\n')
        for line in lines:
            line = line.strip()

            # Skip section header
            if line in ['*Markets', 'Markets', '']:
                continue

            # Skip very short lines
            if len(line) < 15:
                continue

            # Skip marketing/promo content
            if any(skip in line.lower() for skip in ['subscribe', 'click', 'join', 'autopilot', 'litquidity', 'beehiiv']):
                continue

            # Include if it looks like market data
            if len(line) > 20 and any(indicator in line.lower() for indicator in
                ['%', 'bps', 'ath', 'all-time', 'high', 'low', 'rally', 'surge', 'drop',
                 'fell', 'rose', 'climb', 'spread', 'dollar', 'gold', 'silver', 'stock',
                 's&p', 'dow', 'nasdaq', 'index', 'yield', 'bond', 'treasury', 'bitcoin',
                 'oil', 'copper', 'platinum', 'palladium', 'nickel', 'iron', 'commodity']):
                bullet_items.append(line)

    # Filter and create items from bullet points
    seen = set()
    for bullet in bullet_items:
        # Skip duplicates
        if bullet[:50].lower() in seen:
            continue
        seen.add(bullet[:50].lower())

        # Apply include/exclude pattern filtering
        if matches_exclude_pattern(bullet, config):
            continue

        if config.get('require_include_pattern', False):
            if not matches_include_pattern(bullet, config):
                continue

        items.append({
            'url': None,
            'title': bullet,
            'description': 'Markets section bullet point',
            'section': 'Markets',
            'source': 'ExecSum',
            'newsletter_date': None
        })

    return items


def extract_headline_roundup(soup, config: Dict) -> List[Dict]:
    """Extract items from the Headline Roundup section.

    In ExecSum, headlines are often plain text followed by a source link in parentheses.
    E.g., "Data centers will need over $3T in investments through 2030 (BBG)"
    """
    items = []
    headline_items = []

    # Get clean page text with proper line breaks
    page_text = get_clean_page_text(soup)

    # Find all Headline Roundup sections (there may be multiple per newsletter)
    roundup_starts = []
    idx = 0
    while True:
        roundup_idx = page_text.find('Headline Roundup', idx)
        if roundup_idx == -1:
            break
        roundup_starts.append(roundup_idx)
        idx = roundup_idx + 20

    if not roundup_starts:
        return items

    # Section end markers
    section_markers = ['Deal Flow', 'M&A', 'VC', 'IPO', 'Funds', 'Prediction Markets',
                      'Meme Cleanser', "Exec's Picks", 'Execs Picks', 'Related Posts',
                      '*Markets', 'Markets']

    for roundup_idx in roundup_starts:
        # Find where this section ends
        end_idx = len(page_text)
        for marker in section_markers:
            marker_idx = page_text.find(marker, roundup_idx + 20)
            if marker_idx != -1 and marker_idx < end_idx:
                end_idx = marker_idx

        roundup_text = page_text[roundup_idx:end_idx]

        # Split into lines and extract headlines
        lines = roundup_text.split('\n')
        for line in lines:
            line = line.strip()

            # Skip section header and empty lines
            if line in ['Headline Roundup', ''] or len(line) < 20:
                continue

            # Skip marketing/promo content
            skip_words = ['subscribe', 'click', 'join', 'autopilot', 'litquidity',
                         'beehiiv', 'merch', 'fundable', 'here', 'listen', 'take a']
            if any(skip in line.lower() for skip in skip_words):
                continue

            # Check if line looks like a news headline
            # Typically ends with source like (BBG), (RT), (CNBC), etc.
            has_source = bool(re.search(r'\([A-Z]{2,4}\)$|\(Bloomberg\)$|\(Reuters\)$|\(CNBC\)$|\(WSJ\)$|\(FT\)$', line))

            # Include if it has a source suffix or looks substantive (5+ words)
            words = line.split()
            if len(words) >= 5 or has_source:
                # Clean up source suffixes
                clean_line = line
                for suffix in ['(BBG)', '(RT)', '(CNBC)', '(FT)', '(WSJ)', '(NYT)', '(NBC)', '(TC)']:
                    clean_line = clean_line.replace(suffix, '').strip()

                # Skip truncated or incomplete headlines
                if clean_line.endswith('...') or clean_line.endswith('driving') or clean_line.endswith('landmark'):
                    continue

                # Skip very short cleaned lines
                if len(clean_line) < 15:
                    continue

                headline_items.append(clean_line)

    # Deduplicate and filter
    seen = set()
    for headline in headline_items:
        # Skip duplicates
        if headline[:50].lower() in seen:
            continue
        seen.add(headline[:50].lower())

        # Apply exclude pattern filtering
        if matches_exclude_pattern(headline, config):
            continue

        # Apply include pattern filtering if required
        if config.get('require_include_pattern', False):
            if not matches_include_pattern(headline, config):
                continue

        items.append({
            'url': None,
            'title': headline,
            'description': 'Headline Roundup',
            'section': 'Headline Roundup',
            'source': 'ExecSum',
            'newsletter_date': None
        })

    return items


def extract_newsletter_content(url: str, config: Dict) -> Tuple[List[Dict], Optional[str]]:
    """Extract relevant content from an ExecSum newsletter.

    Returns:
        Tuple of (items list, newsletter_date string or None)
    """
    print(f"Fetching: {url}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  Error fetching: {e}")
        return [], None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract newsletter date from the page
    date_str = None

    # Try multiple methods to find the date
    # Method 1: Look for <time> element
    date_elem = soup.find('time')
    if date_elem:
        date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)

    # Method 2: Look for date in meta tags
    if not date_str:
        meta_date = soup.find('meta', {'property': 'article:published_time'}) or \
                    soup.find('meta', {'name': 'date'}) or \
                    soup.find('meta', {'property': 'og:published_time'})
        if meta_date:
            date_str = meta_date.get('content', '')

    # Method 3: Look for common date class names
    if not date_str:
        for class_pattern in ['date', 'published', 'post-date', 'entry-date', 'timestamp']:
            date_elem = soup.find(class_=lambda x: x and class_pattern in str(x).lower())
            if date_elem:
                date_str = date_elem.get_text(strip=True)
                break

    # Method 4: Try to extract from URL (execsum URLs sometimes have dates)
    if not date_str:
        # Look for date pattern in page text near the top
        page_text = soup.get_text()[:2000]  # First 2000 chars
        import re
        date_patterns = [
            r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                break

    if date_str:
        print(f"  Newsletter date: {date_str}")

    items = []
    seen_urls = set()
    seen_titles = set()

    # First, extract Markets section bullet points (no hyperlinks needed)
    if config.get('extract_markets_section', True):
        markets_items = extract_markets_section(soup, config)
        items.extend(markets_items)
        for item in markets_items:
            seen_titles.add(item['title'][:50].lower())
        if markets_items:
            print(f"  Found {len(markets_items)} Markets section bullet points")

    # Extract Headline Roundup items (plain text headlines with source suffixes)
    headline_items = extract_headline_roundup(soup, config)
    items.extend(headline_items)
    for item in headline_items:
        seen_titles.add(item['title'][:50].lower())
    if headline_items:
        print(f"  Found {len(headline_items)} Headline Roundup items")

    # Find all links (for any remaining linked content - skip if already extracted)
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if not href.startswith('http'):
            continue

        clean_url = strip_utm_params(href)
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        # Check if blocked
        if is_blocked_url(clean_url, config):
            continue

        link_text = a_tag.get_text(strip=True)

        # Get parent context - this often contains the actual headline
        parent_text = ''
        headline_text = link_text
        if a_tag.parent:
            parent_text = a_tag.parent.get_text(strip=True)
            # In ExecSum, the headline is often the parent text with the source link at the end
            # e.g., "Japan will slow pace of QT (BBG)" where "(BBG)" is the link
            # Use parent text as headline if link text is just a short source name
            if len(link_text) < 20 and len(parent_text) > len(link_text) + 5:
                # Remove common source suffixes from parent text
                headline_text = parent_text
                for suffix in ['(BBG)', '(RT)', '(CNBC)', '(FT)', '(WSJ)', '(NYT)', '(NBC)',
                              'Bloomberg', 'Reuters', 'CNBC', 'Financial Times', 'Wall Street Journal']:
                    headline_text = headline_text.replace(suffix, '').strip()
                # Clean up trailing punctuation and parentheses
                headline_text = re.sub(r'\s*\(\s*\)\s*$', '', headline_text).strip()
                headline_text = re.sub(r'\s*\($', '', headline_text).strip()

        if not headline_text or len(headline_text) < 10:
            continue

        # Skip items that are clearly not news headlines
        skip_patterns = [
            'here', 'click', 'read more', 'learn more', 'see more',
            'litney', 'stav', 'listen', 'updated for', 'source',
            'hear more', 'all things considered', 'grown up',
            'guide to', 'paradox', 'lessons from', 'rise to',
            'fight', 'Paralympics', 'Formula 1', 'ces speech',
            'path ahead', 'middle east', 'potential scotus'
        ]
        headline_lower = headline_text.lower()
        if any(skip in headline_lower for skip in skip_patterns):
            continue

        # Skip truncated headlines
        if headline_text.endswith('...') or headline_text.endswith('driving') or headline_text.endswith('landmark'):
            continue

        # Skip if headline is just a source name
        source_names = ['bloomberg', 'reuters', 'cnbc', 'wsj', 'financial times',
                       'wall street journal', 'new york times', 'nbc', 'ft']
        if headline_lower.strip() in source_names:
            continue

        # Skip very short headlines that don't look like news
        words = headline_text.split()
        if len(words) < 4:
            continue

        # Skip if we already have this headline from text extraction
        if headline_text[:50].lower() in seen_titles:
            continue

        # Determine section by looking at surrounding content
        section = determine_section(a_tag)

        # Check if section is excluded
        if is_in_excluded_section(section, config):
            continue

        # Check exclude patterns in text
        combined_text = headline_text + ' ' + parent_text
        if matches_exclude_pattern(combined_text, config):
            continue

        # If require_include_pattern is set, item must match at least one include pattern
        if config.get('require_include_pattern', False):
            if not matches_include_pattern(combined_text, config):
                continue

        items.append({
            'url': clean_url,
            'title': headline_text,
            'description': parent_text[:200],
            'section': section,
            'source': get_source_name(clean_url),
            'newsletter_date': date_str
        })

    print(f"  Found {len(items)} relevant items")
    return items, date_str


def determine_section(element) -> str:
    """Determine section based on DOM position."""
    section_keywords = {
        'Headline Roundup': 'Headline Roundup',
        'Deal Flow': 'Deal Flow',
        'M&A': 'M&A / Investments',
        'VC': 'VC',
        'IPO': 'IPO / Listings',
        'SPAC': 'SPAC',
        'Debt': 'Debt',
        'Bankruptcy': 'Bankruptcy / Restructuring',
        'Funds': 'Funds / Secondaries',
        "Exec's Picks": 'Execs Picks',
        'Markets': 'Markets'
    }

    current = element
    for _ in range(30):
        if current is None:
            break

        # Check text content
        text = current.get_text(strip=True) if hasattr(current, 'get_text') else str(current)

        for keyword, section_name in section_keywords.items():
            if keyword in text[:100]:
                return section_name

        # Check previous siblings
        prev = current.find_previous_sibling(['h1', 'h2', 'h3', 'h4', 'strong'])
        if prev:
            prev_text = prev.get_text(strip=True)
            for keyword, section_name in section_keywords.items():
                if keyword in prev_text:
                    return section_name

        current = current.parent

    return 'General'


def fetch_article_content(url: str) -> Optional[str]:
    """Fetch article content for summarization."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()

        # Try to find article content
        article = soup.find('article') or soup.find(class_=re.compile(r'article|content|story|post'))
        if article:
            text = article.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # Clean up text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines[:100])  # Limit to first 100 lines

        return text[:8000]  # Limit to 8000 chars
    except Exception as e:
        print(f"    Could not fetch article: {e}")
        return None


def clean_item_for_audio(text: str) -> str:
    """Clean a single news item for audio output without using AI."""
    # Remove source suffixes
    for suffix in ['(BBG)', '(RT)', '(CNBC)', '(FT)', '(WSJ)', '(NYT)', '(NBC)', '(TC)',
                   '(ExecSum)', '(Bloomberg)', '(Reuters)', '(Financial Times)']:
        text = text.replace(suffix, '').strip()

    # Remove trailing open parenthesis (leftover from incomplete source removal)
    text = re.sub(r'\s*\(\s*$', '', text)

    # Expand common abbreviations
    replacements = [
        (' bps', ' basis points'),
        (' BPS', ' basis points'),
        (' bp ', ' basis point '),
        (' bp.', ' basis point.'),
        (' YoY', ' year over year'),
        (' YTD', ' year to date'),
        (' ATH', ' all-time high'),
        (' QoQ', ' quarter over quarter'),
        (' MoM', ' month over month'),
        (' 1Y ', ' one-year '),
        (' 2Y ', ' two-year '),
        (' 3Y ', ' three-year '),
        (' 4Y ', ' four-year '),
        (' 5Y ', ' five-year '),
        (' 7Y ', ' seven-year '),
        (' 10Y ', ' ten-year '),
        (' 30Y ', ' thirty-year '),
        ('Y-', '-year-'),
        ('2Y-10Y', '2-year-10-year'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    # Clean up double spaces
    while '  ' in text:
        text = text.replace('  ', ' ')

    return text.strip()


def summarize_items_with_ai(items: List[Dict], api_key: str) -> str:
    """Process items for audio output. Uses simple text cleanup instead of AI to avoid dropping items."""
    # Don't use AI for the main processing - it drops items
    # Instead, do simple programmatic cleanup

    output_lines = []

    for item in items:
        title = item.get('title', '').strip()

        # Skip empty or too-short items
        if not title or len(title) < 10:
            continue

        # Skip items that are clearly incomplete or junk
        skip_phrases = ['middle east', "jensen huang's ces speech", 'potential scotus',
                       'path ahead for venezuela', 'litney partners', 'take a listen',
                       'stavmarket', 'updated for 202', 'straight from the source',
                       'schedule a demo', 'hour well spent', 'has built the universe',
                       'managers with over', 'collectively rely on', 'stavtar',
                       'connect to vendors', 'manage their vendors']
        if any(phrase in title.lower() for phrase in skip_phrases):
            continue

        # Skip items ending with incomplete phrases
        if title.endswith('...') or title.endswith('driving') or title.endswith('landmark') or title.endswith(' after') or title.endswith(' its'):
            continue

        # Clean the item for audio
        clean_title = clean_item_for_audio(title)

        if clean_title and len(clean_title) > 10:
            output_lines.append(clean_title)

    return '\n'.join(output_lines)


def create_basic_summary(items: List[Dict]) -> str:
    """Create a basic summary without AI - clean output for audio."""
    output_lines = []

    for item in items:
        title = item.get('title', '').strip()

        # Skip empty or too-short items
        if not title or len(title) < 10:
            continue

        # Skip junk items
        skip_phrases = ['middle east', "jensen huang's ces speech", 'potential scotus',
                       'path ahead for venezuela', 'litney partners', 'take a listen',
                       'stavmarket', 'updated for 202', 'straight from the source',
                       'schedule a demo', 'hour well spent', 'has built the universe',
                       'managers with over', 'collectively rely on', 'stavtar',
                       'connect to vendors', 'manage their vendors']
        if any(phrase in title.lower() for phrase in skip_phrases):
            continue

        # Skip items ending with incomplete phrases
        if title.endswith('...') or title.endswith('driving') or title.endswith('landmark') or title.endswith(' after') or title.endswith(' its'):
            continue

        # Clean the item for audio
        clean_title = clean_item_for_audio(title)

        if clean_title and len(clean_title) > 10:
            output_lines.append(clean_title)

    return '\n'.join(output_lines)


def save_output(content: str, newsletter_urls: List[str]) -> str:
    """Save the output to the weekly folder."""
    week_folder = get_week_folder()

    # Generate filename with date and time to avoid overwriting
    date_str = datetime.now().strftime('%Y-%m-%d_%H%M')
    filename = f"execsum_digest_{date_str}.txt"
    filepath = os.path.join(week_folder, filename)

    # Always write fresh (don't append)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def main():
    parser = argparse.ArgumentParser(description='Process ExecSum newsletters for audio briefing')
    parser.add_argument('urls', nargs='*', help='Newsletter URLs to process')
    parser.add_argument('--urls-file', '-f', help='File containing URLs (one per line)')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI summarization')
    parser.add_argument('--output', '-o', help='Custom output path')

    args = parser.parse_args()

    # Collect URLs
    urls = list(args.urls) if args.urls else []

    if args.urls_file:
        try:
            with open(args.urls_file, 'r') as f:
                urls.extend([line.strip() for line in f if line.strip() and line.startswith('http')])
        except Exception as e:
            print(f"Error reading URLs file: {e}")
            return 1

    if not urls:
        print("No URLs provided. Use: python execsum_processor.py <url> [<url2> ...]")
        return 1

    # Load config
    config = load_config()
    print(f"Loaded ExecSum config: {config.get('name', 'Unknown')}")

    # Extract content from all newsletters
    all_items = []
    newsletter_dates = {}  # Track dates for sorting

    for url in urls:
        items, newsletter_date = extract_newsletter_content(url, config)
        if newsletter_date:
            newsletter_dates[url] = newsletter_date
        for item in items:
            item['source_url'] = url  # Track which newsletter each item came from
        all_items.extend(items)

    # Sort items by newsletter date (oldest first for chronological narrative)
    if newsletter_dates:
        def get_item_date(item):
            url = item.get('source_url', '')
            date_str = newsletter_dates.get(url, '')
            if not date_str:
                return datetime.min

            # Clean up date string - remove timezone suffix if present
            date_str = date_str.split('+')[0].split('Z')[0].strip()

            # Try to parse common date formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%b %d, %Y', '%B %d, %Y', '%Y-%m-%d', '%m/%d/%Y', '%d %b %Y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except (ValueError, TypeError):
                    continue
            return datetime.min  # Put items without dates first

        all_items.sort(key=get_item_date)
        print(f"\nSorted {len(all_items)} items by newsletter date (oldest first)")

    if not all_items:
        print("No relevant content found in newsletters.")
        return 1

    print(f"\nTotal items to process: {len(all_items)}")

    # Generate summary
    if args.no_ai:
        content = create_basic_summary(all_items)
    else:
        api_key = load_api_key()
        if api_key:
            print("\nGenerating AI summary...")
            content = summarize_items_with_ai(all_items, api_key)
        else:
            print("Warning: No API key found. Using basic summary.")
            content = create_basic_summary(all_items)

    # Save output
    if args.output:
        filepath = args.output
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        filepath = save_output(content, urls)

    print(f"\nOutput saved to: {filepath}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
