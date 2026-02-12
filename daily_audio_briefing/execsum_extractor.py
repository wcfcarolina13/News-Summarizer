#!/usr/bin/env python3
"""
ExecSum Newsletter Extractor

Extracts links from ExecSum newsletters for training the extraction config.
Outputs a CSV with resolved URLs (UTM stripped) and a Track? column for marking relevance.

Usage:
    python execsum_extractor.py <newsletter_url> [--output <csv_file>]
    python execsum_extractor.py https://www.execsum.co/p/merry-christmas-from-ours-to-yours
"""

import argparse
import csv
import json
import os
import re
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup


def strip_utm_params(url: str) -> str:
    """Remove UTM and tracking parameters from URL."""
    try:
        parsed = urlparse(url)
        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Remove tracking parameters
        tracking_prefixes = ('utm_', 'ref', 'source', 'campaign', 'medium', 'fbclid', 'gclid',
                            'mc_', 'ml_', '_ga', '_gl', 'sref', 'smid', 'unlocked_article_code')
        filtered_params = {k: v for k, v in params.items()
                         if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)}

        # Rebuild URL
        new_query = urlencode(filtered_params, doseq=True) if filtered_params else ''
        clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                               parsed.params, new_query, ''))
        return clean_url
    except Exception:
        return url


def resolve_redirect(url: str, timeout: int = 10) -> str:
    """Follow redirects to get the final URL."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        return response.url
    except requests.exceptions.RequestException:
        try:
            # Fallback to GET if HEAD fails
            response = requests.get(url, allow_redirects=True, timeout=timeout, stream=True)
            response.close()
            return response.url
        except Exception:
            return url


def get_source_abbrev(url: str) -> str:
    """Extract source abbreviation from URL domain."""
    domain_map = {
        'reuters.com': 'RT',
        'bloomberg.com': 'BBG',
        'ft.com': 'FT',
        'cnbc.com': 'CNBC',
        'nytimes.com': 'NYT',
        'wsj.com': 'WSJ',
        'economist.com': 'ECON',
        'barrons.com': 'BARR',
        'marketwatch.com': 'MW',
        'awealthofcommonsense.com': 'AWOC',
    }

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')

        for key, abbrev in domain_map.items():
            if key in domain:
                return abbrev

        # Return domain without TLD
        parts = domain.split('.')
        return parts[0].upper()[:6]
    except Exception:
        return 'UNK'


def load_config(config_path: str) -> Dict:
    """Load extraction config from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        return {}


def is_blocked_domain(url: str, blocked_domains: List[str]) -> bool:
    """Check if URL domain is in blocked list."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        return any(blocked in domain for blocked in blocked_domains)
    except Exception:
        return False


def matches_exclude_pattern(text: str, exclude_patterns: List[str]) -> bool:
    """Check if text matches any exclusion pattern."""
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in exclude_patterns)


def extract_section(element) -> str:
    """Determine which section a link belongs to based on preceding headers."""
    # Walk up the DOM to find section headers
    current = element
    for _ in range(20):  # Limit search depth
        if current is None:
            break

        # Check previous siblings for headers
        prev = current.find_previous_sibling(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
        if prev:
            text = prev.get_text(strip=True)
            sections = ['Markets', 'Headline Roundup', 'Deal Flow', 'M&A', 'VC',
                       'IPO', 'SPAC', 'Debt', 'Bankruptcy', 'Funds', 'Secondaries',
                       'Exec\'s Picks', 'Crypto Sum', 'Meme Cleanser', 'Prediction Markets']
            for section in sections:
                if section.lower() in text.lower():
                    return section

        current = current.parent

    return 'Unknown'


def extract_newsletter_links(url: str, config: Dict = None) -> List[Dict]:
    """Extract all links from an ExecSum newsletter."""
    print(f"Fetching newsletter: {url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching newsletter: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Get blocked domains from config
    blocked_domains = config.get('blocked_domains', []) if config else []
    exclude_patterns = config.get('exclude_patterns', []) if config else []

    # Find all links in the article content
    links = []
    seen_urls = set()

    # Look for links in the main content area
    content_areas = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and ('content' in str(x).lower() or 'post' in str(x).lower()))
    if not content_areas:
        content_areas = [soup.body] if soup.body else [soup]

    for content in content_areas:
        for a_tag in content.find_all('a', href=True):
            href = a_tag['href']

            # Skip internal/anchor links
            if not href.startswith('http'):
                continue

            # Skip already processed URLs
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Get link text and context
            link_text = a_tag.get_text(strip=True)
            parent_text = ''
            if a_tag.parent:
                parent_text = a_tag.parent.get_text(strip=True)[:300]

            # Determine section
            section = extract_section(a_tag)

            # Check if blocked
            is_blocked = is_blocked_domain(href, blocked_domains)
            matches_exclude = matches_exclude_pattern(link_text + ' ' + parent_text, exclude_patterns)

            links.append({
                'raw_url': href,
                'link_text': link_text,
                'parent_text': parent_text,
                'section': section,
                'is_blocked': is_blocked,
                'matches_exclude': matches_exclude
            })

    return links


def process_links(links: List[Dict], resolve_redirects: bool = True) -> List[Dict]:
    """Process links: resolve redirects and strip UTM parameters."""
    processed = []

    total = len(links)
    for i, link in enumerate(links):
        print(f"Processing link {i+1}/{total}: {link['link_text'][:50]}...")

        url = link['raw_url']

        # Resolve redirect if needed
        if resolve_redirects and not link.get('is_blocked', False):
            try:
                resolved_url = resolve_redirect(url)
            except Exception:
                resolved_url = url
        else:
            resolved_url = url

        # Strip UTM parameters
        clean_url = strip_utm_params(resolved_url)

        # Get source
        source = get_source_abbrev(clean_url)

        processed.append({
            'section': link['section'],
            'title': link['link_text'],
            'url': clean_url,
            'source': source,
            'description': link['parent_text'],
            'is_blocked': link['is_blocked'],
            'matches_exclude': link['matches_exclude'],
            'raw_url': link['raw_url']
        })

    return processed


def export_csv(links: List[Dict], output_path: str, include_blocked: bool = True):
    """Export links to CSV with Track? column."""

    # Filter if needed
    if not include_blocked:
        links = [l for l in links if not l.get('is_blocked') and not l.get('matches_exclude')]

    # Prepare rows
    rows = []
    for link in links:
        # Escape any commas in text fields
        title = link['title'].replace('"', '""') if link['title'] else ''
        description = link['description'].replace('"', '""') if link['description'] else ''

        # Pre-populate Track? based on filtering
        track_default = 'FALSE' if (link.get('is_blocked') or link.get('matches_exclude')) else ''

        rows.append({
            'section': link['section'],
            'title': title,
            'url': link['url'],
            'source': link['source'],
            'description': description[:200],  # Truncate for readability
            'Track?': track_default
        })

    # Write CSV
    fieldnames = ['section', 'title', 'url', 'source', 'description', 'Track?']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nExported {len(rows)} links to: {output_path}")

    # Summary
    blocked_count = sum(1 for l in links if l.get('is_blocked') or l.get('matches_exclude'))
    print(f"  - Pre-marked as FALSE (blocked/excluded): {blocked_count}")
    print(f"  - Needs review: {len(rows) - blocked_count}")


def main():
    parser = argparse.ArgumentParser(description='Extract links from ExecSum newsletter for training')
    parser.add_argument('url', help='ExecSum newsletter URL')
    parser.add_argument('--output', '-o', default='execsum_training.csv', help='Output CSV file path')
    parser.add_argument('--config', '-c', default=None, help='Path to execsum.json config')
    parser.add_argument('--no-resolve', action='store_true', help='Skip resolving redirects')
    parser.add_argument('--include-blocked', action='store_true', help='Include blocked domains in output')

    args = parser.parse_args()

    # Find config file
    config_path = args.config
    if not config_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'extraction_instructions', 'execsum.json')

    config = load_config(config_path) if os.path.exists(config_path) else {}

    # Extract links
    links = extract_newsletter_links(args.url, config)

    if not links:
        print("No links found!")
        return 1

    print(f"\nFound {len(links)} links")

    # Process links
    processed = process_links(links, resolve_redirects=not args.no_resolve)

    # Export to CSV
    export_csv(processed, args.output, include_blocked=args.include_blocked)

    return 0


if __name__ == '__main__':
    sys.exit(main())
