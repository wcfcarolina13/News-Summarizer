"""
Data CSV Processor - Extract links and data from various sources into CSV format.

Supports:
- Newsletters (beehiiv, Substack, etc.)
- Articles
- RSS Feeds
- YouTube videos
- Generic web pages

Features:
- Resolves redirect URLs (beehiiv tracking links)
- Strips tracking parameters (utm_*, etc.)
- Custom extraction rules per source/domain
- Appends to existing CSV sheets
"""

import csv
import os
import re
import json
import ssl
import urllib.request
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Create SSL context that's more permissive for sites with strict SSL configs
try:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1')
except:
    SSL_CONTEXT = None


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ExtractedItem:
    """Represents a single extracted item from a source."""
    title: str = ""
    url: str = ""
    original_url: str = ""  # Before redirect resolution
    source_name: str = ""
    source_url: str = ""
    category: str = ""
    description: str = ""
    author: str = ""
    date_published: str = ""
    date_extracted: str = field(default_factory=lambda: datetime.now().isoformat())
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, flattening custom_fields."""
        base = asdict(self)
        custom = base.pop('custom_fields', {})
        return {**base, **custom}


@dataclass
class ExtractionConfig:
    """Configuration for extraction behavior."""
    resolve_redirects: bool = True
    strip_tracking_params: bool = True
    tracking_params: List[str] = field(default_factory=lambda: [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        '_bhlid', 'ref', 'source', 'mc_cid', 'mc_eid', 'fbclid', 'gclid',
        'msclkid', 'twclid', 'igshid', 's', 'si'  # social tracking params
    ])
    timeout: int = 10
    max_workers: int = 5
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # CSV output settings
    csv_columns: List[str] = field(default_factory=lambda: [
        'title', 'url', 'source_name', 'category', 'description',
        'author', 'date_published', 'date_extracted'
    ])
    append_mode: bool = True


# =============================================================================
# URL UTILITIES
# =============================================================================

class URLProcessor:
    """Handles URL cleaning, redirect resolution, and parameter stripping."""

    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.user_agent})
        self._redirect_cache: Dict[str, str] = {}

    def clean_url(self, url: str) -> str:
        """Strip tracking parameters from URL."""
        if not self.config.strip_tracking_params:
            return url

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)

            # Remove tracking parameters
            cleaned_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in [p.lower() for p in self.config.tracking_params]
            }

            # Rebuild URL
            new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""
            cleaned = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                ""  # Remove fragment
            ))
            return cleaned.rstrip('?')
        except Exception:
            return url

    def resolve_redirect(self, url: str) -> str:
        """Follow redirects to get final destination URL."""
        if not self.config.resolve_redirects:
            return url

        # Check cache first
        if url in self._redirect_cache:
            return self._redirect_cache[url]

        try:
            # Use HEAD request first (faster), fall back to GET
            response = self.session.head(
                url,
                allow_redirects=True,
                timeout=self.config.timeout
            )
            final_url = response.url

            # If HEAD didn't work well, try GET
            if response.status_code >= 400:
                response = self.session.get(
                    url,
                    allow_redirects=True,
                    timeout=self.config.timeout
                )
                final_url = response.url

            self._redirect_cache[url] = final_url
            return final_url
        except Exception as e:
            print(f"  [!] Could not resolve redirect for {url[:50]}...: {e}")
            return url

    def process_url(self, url: str) -> tuple[str, str]:
        """
        Process URL: resolve redirects and clean parameters.
        Returns (cleaned_url, original_url).
        """
        original = url

        # Resolve redirects first
        resolved = self.resolve_redirect(url)

        # Then clean tracking params
        cleaned = self.clean_url(resolved)

        return cleaned, original

    def is_internal_link(self, url: str, base_domain: str) -> bool:
        """Check if URL is internal to the base domain."""
        try:
            parsed = urlparse(url)
            return base_domain in parsed.netloc
        except:
            return False

    def normalize_url(self, url: str, base_url: str) -> str:
        """Convert relative URLs to absolute."""
        if url.startswith('http'):
            return url
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{url}"
        return base_url.rstrip('/') + '/' + url


# =============================================================================
# SOURCE-SPECIFIC EXTRACTORS
# =============================================================================

class BaseExtractor:
    """Base class for source-specific extractors."""

    name = "base"
    supported_domains: List[str] = []

    def __init__(self, url_processor: URLProcessor, config: ExtractionConfig):
        self.url_processor = url_processor
        self.config = config

    def can_handle(self, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in self.supported_domains)

    def extract(self, url: str, html: str, custom_instructions: Dict = None) -> List[ExtractedItem]:
        """Extract items from the source. Override in subclasses."""
        raise NotImplementedError

    def _get_soup(self, html: str) -> BeautifulSoup:
        """Parse HTML with BeautifulSoup."""
        return BeautifulSoup(html, 'html.parser')


class BeehiivExtractor(BaseExtractor):
    """Extractor for Beehiiv newsletters (like CryptoSum)."""

    name = "beehiiv"
    supported_domains = ["beehiiv.com"]

    def extract(self, url: str, html: str, custom_instructions: Dict = None) -> List[ExtractedItem]:
        """Extract all links and topics from a Beehiiv newsletter."""
        soup = self._get_soup(html)
        items = []
        seen_urls = set()  # Track URLs to avoid duplicates

        # Get newsletter metadata
        source_name = self._extract_source_name(soup, url)
        pub_date = self._extract_date(soup, url)

        # Get the main content area
        content_area = soup.find('div', class_='post-content') or soup.find('article') or soup.body

        if not content_area:
            return items

        # Extract all links with their context
        current_category = "General"

        # Only iterate over container elements and headers (not standalone <a> tags to avoid duplicates)
        for element in content_area.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
            # Track category headers
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                header_text = element.get_text(strip=True)
                if header_text and len(header_text) < 100:
                    current_category = header_text
                continue

            # Extract links from paragraphs and list items
            links = element.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                if not href or href.startswith('#') or href.startswith('mailto:'):
                    continue

                # Skip internal beehiiv links (subscribe, share, etc.)
                if self._is_internal_link(href, url):
                    continue

                # Get link text and surrounding context
                link_text = link.get_text(strip=True)
                context = self._get_link_context(link, element)

                # Handle beehiiv redirect links (extract dest parameter)
                original_url = href
                if 'links.beehiiv.com' in href or 'beehiiv.com/r/' in href:
                    extracted_dest = self._extract_beehiiv_dest(href)
                    if extracted_dest:
                        href = extracted_dest

                # Process URL (resolve redirect, clean params)
                cleaned_url, _ = self.url_processor.process_url(href)

                # Skip duplicates
                if cleaned_url in seen_urls:
                    continue
                seen_urls.add(cleaned_url)

                # Apply custom instructions filtering if provided
                if custom_instructions:
                    if not self._passes_filter(cleaned_url, link_text, context, current_category, custom_instructions):
                        continue

                item = ExtractedItem(
                    title=link_text or self._extract_title_from_url(cleaned_url),
                    url=cleaned_url,
                    original_url=original_url,
                    source_name=source_name,
                    source_url=url,
                    category=current_category,
                    description=context,
                    date_published=pub_date,
                )

                # Add custom fields if specified
                if custom_instructions and 'custom_fields' in custom_instructions:
                    for field_name, extractor_func in custom_instructions['custom_fields'].items():
                        try:
                            item.custom_fields[field_name] = extractor_func(link, element, soup)
                        except:
                            item.custom_fields[field_name] = ""

                items.append(item)

        return items

    def _extract_source_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract the newsletter/publication name."""
        # Try meta tags first
        og_site = soup.find('meta', property='og:site_name')
        if og_site:
            return og_site.get('content', '')

        # Try title
        title = soup.find('title')
        if title:
            return title.get_text(strip=True).split('|')[0].strip()

        # Fall back to domain
        parsed = urlparse(url)
        return parsed.netloc.split('.')[0].title()

    def _extract_date(self, soup: BeautifulSoup, url: str = None) -> str:
        """Extract publication date from newsletter."""
        # Try meta tags first (most reliable)
        date_meta = soup.find('meta', property='article:published_time')
        if date_meta:
            content = date_meta.get('content', '')
            if content and len(content) >= 10:
                return content[:10]

        # Try og:published_time
        og_date = soup.find('meta', property='og:published_time')
        if og_date:
            content = og_date.get('content', '')
            if content and len(content) >= 10:
                return content[:10]

        # Try time elements with datetime attribute
        time_elem = soup.find('time', datetime=True)
        if time_elem:
            dt = time_elem.get('datetime', '')
            if dt and len(dt) >= 10:
                return dt[:10]

        # Try any time element text
        time_elem = soup.find('time')
        if time_elem:
            text = time_elem.get_text(strip=True)
            # Try to parse common date formats
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)
            if date_match:
                return date_match.group(1).replace('/', '-')

        # Try to extract date from URL (beehiiv often has /p/YYYY-MM-DD-slug format)
        if url:
            url_date_match = re.search(r'/p/(\d{4}-\d{2}-\d{2})', url)
            if url_date_match:
                return url_date_match.group(1)

        # Try schema.org datePublished
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    date_pub = data.get('datePublished', '')
                    if date_pub and len(date_pub) >= 10:
                        return date_pub[:10]
            except:
                pass

        # Look for date in common page elements
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # 2024-01-15 or 2024/01/15
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})',  # January 15, 2024
        ]

        # Check common date container classes
        for selector in ['.date', '.post-date', '.published', '.meta-date', '[class*="date"]']:
            date_elem = soup.select_one(selector)
            if date_elem:
                text = date_elem.get_text(strip=True)
                for pattern in date_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        date_str = match.group(1)
                        # Normalize format
                        if '-' in date_str or '/' in date_str:
                            return date_str.replace('/', '-')[:10]
                        # Try parsing text dates like "January 15, 2024"
                        try:
                            from dateutil import parser
                            parsed = parser.parse(date_str)
                            return parsed.strftime('%Y-%m-%d')
                        except:
                            pass

        # Fallback: return empty string to indicate no date found
        # This is better than returning current date which is misleading
        return ""

    def _is_internal_link(self, href: str, source_url: str) -> bool:
        """Check if link is internal to the newsletter platform."""
        internal_patterns = [
            'beehiiv.com/subscribe',
            'beehiiv.com/login',
            '/subscribe',
            '/share',
            'twitter.com/intent',
            'facebook.com/sharer',
            'linkedin.com/share',
            'threads.net/intent',
            'mailto:',
            '#'
        ]
        return any(pattern in href.lower() for pattern in internal_patterns)

    def _extract_beehiiv_dest(self, url: str) -> str:
        """Extract destination URL from beehiiv redirect link."""
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # beehiiv uses 'dest' parameter for destination
            if 'dest' in query_params:
                return query_params['dest'][0]

            # Some use 'url' parameter
            if 'url' in query_params:
                return query_params['url'][0]

            # Try to find any URL in query params
            for key, values in query_params.items():
                for val in values:
                    if val.startswith('http'):
                        return val

            return ""
        except:
            return ""

    def _get_link_context(self, link, parent_element) -> str:
        """Get the text context around a link."""
        if parent_element and parent_element != link:
            return parent_element.get_text(strip=True)[:200]
        return ""

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from URL path if no link text."""
        parsed = urlparse(url)
        path = parsed.path.strip('/').split('/')[-1]
        # Convert slugs to readable text
        return path.replace('-', ' ').replace('_', ' ').title()[:100]

    def _passes_filter(self, url: str, text: str, context: str, category: str, instructions: Dict) -> bool:
        """Check if item passes custom instruction filters."""
        # Require URL if specified
        if instructions.get('require_url', False):
            if not url or not url.strip() or url.strip() == '#':
                return False

        # Exclude categories
        exclude_categories = instructions.get('exclude_categories', [])
        if exclude_categories and category:
            if any(cat.lower() in category.lower() for cat in exclude_categories):
                return False

        # Include patterns (empty list = include all)
        include_patterns = instructions.get('include_patterns', [])
        if include_patterns:  # Only filter if list is non-empty
            combined = f"{url} {text} {context}".lower()
            if not any(p.lower() in combined for p in include_patterns):
                return False

        # Exclude patterns
        exclude_patterns = instructions.get('exclude_patterns', [])
        if exclude_patterns:
            combined = f"{url} {text} {context}".lower()
            if any(p.lower() in combined for p in exclude_patterns):
                return False

        # Domain whitelist (empty list = allow all)
        allowed_domains = instructions.get('allowed_domains', [])
        if allowed_domains:  # Only filter if list is non-empty
            parsed = urlparse(url)
            if not any(d in parsed.netloc for d in allowed_domains):
                return False

        # Domain blacklist
        blocked_domains = instructions.get('blocked_domains', [])
        if blocked_domains:
            parsed = urlparse(url)
            if any(d in parsed.netloc for d in blocked_domains):
                return False

        return True


class GenericWebExtractor(BaseExtractor):
    """Generic extractor for any web page."""

    name = "generic"
    supported_domains = []  # Handles any domain as fallback

    def can_handle(self, url: str) -> bool:
        """Generic extractor handles any URL."""
        return True

    def extract(self, url: str, html: str, custom_instructions: Dict = None) -> List[ExtractedItem]:
        """Extract all external links from a web page."""
        soup = self._get_soup(html)
        items = []

        source_name = self._extract_source_name(soup, url)
        parsed_source = urlparse(url)

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if not href or href.startswith('#') or href.startswith('mailto:'):
                continue

            # Normalize URL
            full_url = self.url_processor.normalize_url(href, url)

            # Skip internal links
            parsed = urlparse(full_url)
            if parsed.netloc == parsed_source.netloc:
                continue

            # Process URL
            cleaned_url, original_url = self.url_processor.process_url(full_url)

            link_text = link.get_text(strip=True)

            item = ExtractedItem(
                title=link_text or self._extract_title_from_url(cleaned_url),
                url=cleaned_url,
                original_url=original_url,
                source_name=source_name,
                source_url=url,
                category="External Link",
            )
            items.append(item)

        return items

    def _extract_source_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page/site name."""
        og_site = soup.find('meta', property='og:site_name')
        if og_site:
            return og_site.get('content', '')

        title = soup.find('title')
        if title:
            return title.get_text(strip=True)[:50]

        return urlparse(url).netloc

    def _extract_title_from_url(self, url: str) -> str:
        """Extract title from URL."""
        parsed = urlparse(url)
        path = parsed.path.strip('/').split('/')[-1]
        return path.replace('-', ' ').replace('_', ' ').title()[:100] or parsed.netloc


class RSSExtractor(BaseExtractor):
    """Extractor for RSS/Atom feeds."""

    name = "rss"
    supported_domains = []

    def can_handle(self, url: str) -> bool:
        """Check if URL is an RSS feed."""
        return any(ext in url.lower() for ext in ['.rss', '.xml', '/feed', '/rss', 'atom'])

    def extract(self, url: str, html: str, custom_instructions: Dict = None) -> List[ExtractedItem]:
        """Extract items from RSS feed."""
        soup = BeautifulSoup(html, 'xml')
        items = []

        # Get feed title
        feed_title = soup.find('title')
        source_name = feed_title.get_text(strip=True) if feed_title else urlparse(url).netloc

        # Handle both RSS and Atom formats
        entries = soup.find_all('item') or soup.find_all('entry')

        for entry in entries:
            title_elem = entry.find('title')
            link_elem = entry.find('link')
            desc_elem = entry.find('description') or entry.find('summary') or entry.find('content')
            date_elem = entry.find('pubDate') or entry.find('published') or entry.find('updated')
            author_elem = entry.find('author') or entry.find('dc:creator')

            # Get link (RSS vs Atom format)
            if link_elem:
                link_url = link_elem.get('href') or link_elem.get_text(strip=True)
            else:
                continue

            cleaned_url, original_url = self.url_processor.process_url(link_url)

            item = ExtractedItem(
                title=title_elem.get_text(strip=True) if title_elem else "",
                url=cleaned_url,
                original_url=original_url,
                source_name=source_name,
                source_url=url,
                category="RSS Feed",
                description=desc_elem.get_text(strip=True)[:500] if desc_elem else "",
                date_published=date_elem.get_text(strip=True) if date_elem else "",
                author=author_elem.get_text(strip=True) if author_elem else "",
            )
            items.append(item)

        return items


# =============================================================================
# CSV MANAGER
# =============================================================================

class CSVManager:
    """Handles CSV file operations with append support."""

    def __init__(self, config: ExtractionConfig):
        self.config = config

    def write_items(self, items: List[ExtractedItem], output_path: str,
                    custom_columns: List[str] = None) -> str:
        """
        Write extracted items to CSV file.

        Args:
            items: List of ExtractedItem objects
            output_path: Path to CSV file
            custom_columns: Optional custom column order

        Returns:
            Path to the written CSV file
        """
        if not items:
            print("No items to write.")
            return output_path

        columns = list(custom_columns or self.config.csv_columns)

        # Define the canonical Grid column order to match the user's sheet
        grid_column_order = [
            'grid_asset_id', 'grid_matched', 'grid_profile_id', 'grid_confidence',
            'grid_entity_name', 'grid_match_count', 'grid_product_id', 'grid_profile_name',
            'grid_product_name', 'grid_entity_id', 'grid_asset_name', 'grid_subjects',
            'comments', 'grid_asset_ticker'
        ]

        # Collect all custom fields from items
        all_custom_fields = set()
        for item in items:
            all_custom_fields.update(item.custom_fields.keys())

        # Add Grid columns in the correct order, then any remaining custom fields
        for field in grid_column_order:
            if field in all_custom_fields and field not in columns:
                columns.append(field)
                all_custom_fields.discard(field)

        # Add any remaining custom fields not in the Grid order
        for field in sorted(all_custom_fields):
            if field not in columns:
                columns.append(field)

        # Check if file exists for append mode
        file_exists = os.path.exists(output_path)
        mode = 'a' if (self.config.append_mode and file_exists) else 'w'
        write_header = not (self.config.append_mode and file_exists)

        # If appending, read existing columns to maintain consistency
        if self.config.append_mode and file_exists:
            existing_columns = self._read_existing_columns(output_path)
            if existing_columns:
                # Merge columns, keeping existing order and adding new ones
                for col in columns:
                    if col not in existing_columns:
                        existing_columns.append(col)
                columns = existing_columns

        with open(output_path, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')

            if write_header:
                writer.writeheader()

            # Checkbox columns that should default to FALSE
            checkbox_columns = {'Processed', 'Added'}

            for item in items:
                row = item.to_dict()
                # Add default FALSE for checkbox columns not in row
                for col in columns:
                    if col in checkbox_columns and col not in row:
                        row[col] = 'FALSE'
                writer.writerow(row)

        print(f"{'Appended' if mode == 'a' else 'Wrote'} {len(items)} items to {output_path}")
        return output_path

    def _read_existing_columns(self, path: str) -> List[str]:
        """Read column headers from existing CSV."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                return next(reader, [])
        except:
            return []

    def deduplicate(self, output_path: str, key_column: str = 'url') -> int:
        """Remove duplicate entries from CSV based on key column."""
        if not os.path.exists(output_path):
            return 0

        seen = set()
        unique_rows = []
        duplicates = 0

        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames

            for row in reader:
                key = row.get(key_column, '')
                if key and key not in seen:
                    seen.add(key)
                    unique_rows.append(row)
                else:
                    duplicates += 1

        if duplicates > 0:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows(unique_rows)

            print(f"Removed {duplicates} duplicate entries.")

        return duplicates


# =============================================================================
# MAIN PROCESSOR
# =============================================================================

class DataCSVProcessor:
    """
    Main processor for extracting data from various sources into CSV format.

    Usage:
        processor = DataCSVProcessor()

        # Process a single URL
        items = processor.process_url("https://cryptosum.beehiiv.com/p/...")
        processor.save_to_csv(items, "output.csv")

        # Process multiple URLs
        all_items = processor.process_urls(["url1", "url2", ...])
        processor.save_to_csv(all_items, "output.csv")

        # With custom instructions
        instructions = {
            "include_patterns": ["bitcoin", "ethereum"],
            "exclude_patterns": ["sponsor", "advertisement"],
            "blocked_domains": ["twitter.com", "facebook.com"]
        }
        items = processor.process_url(url, custom_instructions=instructions)
    """

    def __init__(self, config: ExtractionConfig = None):
        self.config = config or ExtractionConfig()
        self.url_processor = URLProcessor(self.config)
        self.csv_manager = CSVManager(self.config)

        # Register extractors (order matters - specific before generic)
        self.extractors: List[BaseExtractor] = [
            BeehiivExtractor(self.url_processor, self.config),
            RSSExtractor(self.url_processor, self.config),
            GenericWebExtractor(self.url_processor, self.config),
        ]

        # Source-specific custom instructions
        self.source_instructions: Dict[str, Dict] = {}

    def register_source_instructions(self, domain_pattern: str, instructions: Dict):
        """
        Register custom extraction instructions for a specific domain.

        Args:
            domain_pattern: Domain pattern to match (e.g., "cryptosum", "beehiiv.com")
            instructions: Dictionary of extraction instructions
        """
        self.source_instructions[domain_pattern] = instructions

    def _get_instructions_for_url(self, url: str, custom_instructions: Dict = None) -> Dict:
        """Get combined instructions for a URL."""
        combined = {}

        # Check registered source instructions
        parsed = urlparse(url)
        for pattern, instructions in self.source_instructions.items():
            if pattern.lower() in parsed.netloc.lower() or pattern.lower() in url.lower():
                combined.update(instructions)
                break

        # Override with custom instructions if provided
        if custom_instructions:
            combined.update(custom_instructions)

        return combined

    def _fetch_content(self, url: str) -> str:
        """Fetch HTML content from URL with multiple fallback methods."""
        # Browser-like headers to bypass bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        # Method 1: Try requests first with full browser headers
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    [!] requests failed: {e}")

        # Method 2: Try urllib with custom SSL context
        try:
            req = urllib.request.Request(url, headers=headers)
            if SSL_CONTEXT:
                with urllib.request.urlopen(req, timeout=self.config.timeout, context=SSL_CONTEXT) as response:
                    return response.read().decode('utf-8', errors='ignore')
            else:
                with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                    return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"    [!] urllib failed: {e}")

        # Method 3: Try with no SSL verification
        try:
            import ssl
            no_verify_ctx = ssl.create_default_context()
            no_verify_ctx.check_hostname = False
            no_verify_ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.config.timeout, context=no_verify_ctx) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"    [!] SSL bypass failed: {e}")

        # All direct fetch methods failed
        return ""

    def _web_search_fallback(self, query: str, original_url: str) -> str:
        """
        Search for article content via web search when direct fetch fails.
        Uses DuckDuckGo HTML search (no API key needed).
        Returns article text if found, empty string otherwise.
        """
        try:
            # Clean up query - use headline without source prefix
            search_query = query.strip()
            if len(search_query) < 10:
                return ""

            print(f"    [*] Searching for article: {search_query[:50]}...")

            # Search DuckDuckGo HTML
            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(search_query + ' crypto news')}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
            }

            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                search_html = response.read().decode('utf-8', errors='ignore')

            # Parse search results
            soup = BeautifulSoup(search_html, 'lxml')
            results = soup.find_all('a', class_='result__a')

            # Try to fetch from alternative sources (skip the original blocked domain)
            original_domain = urllib.parse.urlparse(original_url).netloc
            blocked_domains = ['theblock.co', 'thedefiant.io', 'finsmes.com']  # Known to block

            for result in results[:5]:
                raw_url = result.get('href', '')

                # DuckDuckGo returns redirect URLs like //duckduckgo.com/l/?uddg=https%3A...
                # Extract the actual URL from the uddg parameter
                if 'uddg=' in raw_url:
                    try:
                        parsed = urllib.parse.urlparse(raw_url)
                        params = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in params:
                            result_url = urllib.parse.unquote(params['uddg'][0])
                        else:
                            continue
                    except Exception:
                        continue
                elif raw_url.startswith('http'):
                    result_url = raw_url
                else:
                    continue

                result_domain = urllib.parse.urlparse(result_url).netloc
                if result_domain == original_domain or any(bd in result_domain for bd in blocked_domains):
                    continue

                # Try to fetch this alternative source
                try:
                    alt_req = urllib.request.Request(result_url, headers=headers)
                    with urllib.request.urlopen(alt_req, timeout=10) as alt_response:
                        alt_html = alt_response.read().decode('utf-8', errors='ignore')

                    # Extract article body
                    alt_text = self._extract_article_body(alt_html)
                    if alt_text and len(alt_text) > 200:
                        print(f"    [*] Found alternative: {result_domain}")
                        return alt_text

                except Exception:
                    continue

            print(f"    [!] No accessible alternative sources found")
            return ""

        except Exception as e:
            print(f"    [!] Web search failed: {e}")
            return ""

    def _get_extractor(self, url: str) -> BaseExtractor:
        """Get the appropriate extractor for a URL."""
        for extractor in self.extractors:
            if extractor.can_handle(url):
                return extractor
        return self.extractors[-1]  # Generic fallback

    def process_url(self, url: str, custom_instructions: Dict = None) -> List[ExtractedItem]:
        """
        Process a single URL and extract items.

        Args:
            url: URL to process
            custom_instructions: Optional custom extraction instructions

        Returns:
            List of ExtractedItem objects
        """
        print(f"\n[*] Processing: {url[:80]}...")

        # Fetch content
        html = self._fetch_content(url)
        if not html:
            return []

        # Get appropriate extractor
        extractor = self._get_extractor(url)
        print(f"    Using extractor: {extractor.name}")

        # Get combined instructions
        instructions = self._get_instructions_for_url(url, custom_instructions)

        # Extract items
        items = extractor.extract(url, html, instructions)
        print(f"    Extracted {len(items)} items")

        # Resolve redirects in parallel for speed
        if self.config.resolve_redirects and items:
            print(f"    Resolving redirects...")
            self._resolve_redirects_parallel(items)

        return items

    def process_urls(self, urls: List[str], custom_instructions: Dict = None) -> List[ExtractedItem]:
        """
        Process multiple URLs and combine results.

        Args:
            urls: List of URLs to process
            custom_instructions: Optional custom extraction instructions

        Returns:
            Combined list of ExtractedItem objects
        """
        all_items = []
        for url in urls:
            items = self.process_url(url, custom_instructions)
            all_items.extend(items)
        return all_items

    def process_html(self, html: str, source_url: str = "",
                     custom_instructions: Dict = None) -> List[ExtractedItem]:
        """
        Process HTML content directly (when you already have the HTML).

        Args:
            html: HTML content to process
            source_url: URL of the source (for metadata and extractor selection)
            custom_instructions: Optional custom extraction instructions

        Returns:
            List of ExtractedItem objects
        """
        print(f"\n[*] Processing HTML content...")
        if source_url:
            print(f"    Source: {source_url[:80]}")

        # Get appropriate extractor
        extractor = self._get_extractor(source_url) if source_url else self.extractors[-1]
        print(f"    Using extractor: {extractor.name}")

        # Get combined instructions
        instructions = self._get_instructions_for_url(source_url, custom_instructions) if source_url else custom_instructions

        # Extract items
        items = extractor.extract(source_url, html, instructions)
        print(f"    Extracted {len(items)} items")

        # Resolve redirects in parallel for speed
        if self.config.resolve_redirects and items:
            print(f"    Resolving redirects...")
            self._resolve_redirects_parallel(items)

        return items

    def process_file(self, file_path: str, source_url: str = "",
                     custom_instructions: Dict = None) -> List[ExtractedItem]:
        """
        Process HTML content from a local file.

        Args:
            file_path: Path to HTML file
            source_url: URL of the source (for metadata)
            custom_instructions: Optional custom extraction instructions

        Returns:
            List of ExtractedItem objects
        """
        print(f"\n[*] Processing file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()
            return self.process_html(html, source_url, custom_instructions)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return []

    def _resolve_redirects_parallel(self, items: List[ExtractedItem]):
        """Resolve redirects for items in parallel."""
        # Only resolve items that still have their original URL
        to_resolve = [(i, item) for i, item in enumerate(items)
                      if item.url == item.original_url or 'beehiiv' in item.original_url]

        if not to_resolve:
            return

        def resolve_item(index_item):
            i, item = index_item
            cleaned, _ = self.url_processor.process_url(item.original_url)
            return i, cleaned

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = [executor.submit(resolve_item, item) for item in to_resolve]
            for future in as_completed(futures):
                try:
                    i, cleaned_url = future.result()
                    items[i].url = cleaned_url
                except Exception as e:
                    pass  # Keep original URL on error

    def save_to_csv(self, items: List[ExtractedItem], output_path: str,
                    custom_columns: List[str] = None) -> str:
        """
        Save extracted items to CSV file.

        Args:
            items: List of ExtractedItem objects
            output_path: Path to output CSV file
            custom_columns: Optional custom column order

        Returns:
            Path to the written CSV file
        """
        return self.csv_manager.write_items(items, output_path, custom_columns)

    def enrich_with_grid(self, items: List[ExtractedItem], api_key: str = None, debug: bool = False) -> List[ExtractedItem]:
        """
        Enrich extracted items with The Grid API data.

        Adds to each item's custom_fields:
        - grid_matched: TRUE/FALSE
        - grid_entity_id: The Grid entity ID
        - grid_entity_name: Entity name in The Grid
        - grid_entity_type: profile/product/asset
        - grid_category: Category from The Grid
        - grid_tags: Tags from The Grid
        - tgs_recommendation: Recommended TGS data to use

        Args:
            items: List of ExtractedItem objects
            api_key: Optional Grid API key
            debug: If True, print detailed matching info

        Returns:
            Items with Grid data added to custom_fields
        """
        try:
            from grid_api import GridEntityMatcher
        except ImportError:
            print("  [!] Grid API module not available")
            return items

        print(f"\n[*] Enriching {len(items)} items with Grid data...")

        matcher = GridEntityMatcher(api_key=api_key)

        for i, item in enumerate(items):
            # Combine title + description for matching
            full_text = f"{item.title} {item.description}"

            if debug:
                print(f"\n  [{i+1}] DEBUG:")
                print(f"       Title: {item.title[:60]}...")
                print(f"       Description: {item.description[:60]}..." if item.description else "       Description: (empty)")
                # Show extracted keywords
                keywords = matcher.extract_keywords(full_text)
                print(f"       Keywords: {keywords}")

            match = matcher.match_entity(item.title, item.url, item.description)

            # Add Grid data to custom_fields
            grid_data = match.to_dict()
            for key, value in grid_data.items():
                item.custom_fields[key] = value

            if match.matched:
                # Show all matched subjects
                subjects = ", ".join(m.name for m in match.matches[:3])  # Show top 3
                extra = f" (+{len(match.matches)-3} more)" if len(match.matches) > 3 else ""
                conf = match.primary.confidence if match.primary else 0
                print(f"  [{i+1}] ✓ {item.title[:40]}... → {subjects}{extra} (conf: {conf:.2f})")
            else:
                # Show why it didn't match
                if debug:
                    print(f"       No match found (no keywords or low confidence)")
                else:
                    print(f"  [{i+1}] ✗ {item.title[:40]}...")

        matched_count = sum(1 for item in items if item.custom_fields.get("grid_matched"))
        print(f"\n[*] Matched {matched_count}/{len(items)} items to Grid entities")

        return items

    def research_articles(self, items: List[ExtractedItem],
                          categories: List[str] = None,
                          search_terms: List[str] = None,
                          only_unmatched: bool = True,
                          all_items: bool = False,
                          api_key: str = None) -> List[ExtractedItem]:
        """
        Research article content for blockchain/ecosystem mentions.

        For items in specified categories (e.g., 'Venture Capital', 'Launches'),
        fetches the article content and searches for mentions of specified terms.
        Results are added to item.custom_fields['comments'].

        Args:
            items: List of ExtractedItem objects
            categories: Categories to research (default: ['Venture Capital', 'Launches'])
            search_terms: Terms to search for (default: ['Solana', 'Starknet', 'Tether'])
            only_unmatched: Only research items that didn't get a Grid match
            all_items: If True, research ALL items regardless of category
            api_key: Gemini API key for LLM analysis (optional)

        Returns:
            Items with 'comments' field populated for researched articles
        """
        if categories is None:
            categories = ['Venture Capital', 'Launches']
        if search_terms is None:
            # Only search for priority ecosystems - others are covered by Grid matches
            search_terms = ['Solana', 'Starknet', 'Tether', 'USDT', 'SOL']

        # Categories to exclude from research
        exclude_categories = [
            'extra reads', 'extra read',
            'regulatory', 'regulation',
            'cybersecurity', 'security', 'hacks',
            'legal', 'enforcement'
        ]

        # Normalize categories for comparison
        categories_lower = [c.lower() for c in categories]

        # Build regex pattern for efficient searching
        pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in search_terms) + r')\b',
            re.IGNORECASE
        )

        # Filter items to research
        items_to_research = []
        for item in items:
            item_cat = item.category.lower() if item.category else ''

            # Skip excluded categories (even when all_items is True)
            if any(exc in item_cat for exc in exclude_categories):
                continue

            # Check if category matches (skip if all_items is True)
            if not all_items:
                cat_match = any(cat in item_cat for cat in categories_lower)
                if not cat_match:
                    continue

            # Check if we should skip matched items
            if only_unmatched and item.custom_fields.get('grid_matched'):
                continue

            # Check if we have a valid URL
            if not item.url or not item.url.startswith('http'):
                continue

            items_to_research.append(item)

        if not items_to_research:
            scope = "all categories" if all_items else f"categories: {categories}"
            print(f"\n[*] No items to research ({scope})")
            return items

        scope_msg = "all items" if all_items else f"categories: {', '.join(categories)}"
        print(f"\n[*] Researching {len(items_to_research)} articles ({scope_msg}) for mentions of: {', '.join(search_terms)}")

        # Import Grid matcher once
        try:
            from grid_api import GridEntityMatcher
            grid_available = True
        except ImportError:
            grid_available = False

        for i, item in enumerate(items_to_research):
            try:
                print(f"  [{i+1}/{len(items_to_research)}] Fetching: {item.url[:60]}...")

                # Fetch article content
                html = self._fetch_content(item.url)
                article_text = ""

                if html:
                    # Extract ONLY the main article body (avoid related articles, sidebars, etc.)
                    article_text = self._extract_article_body(html)

                # If direct fetch failed or extracted nothing, try web search fallback
                if not article_text or len(article_text) < 100:
                    # Use the item description as search query
                    search_query = item.description if item.description else item.title
                    article_text = self._web_search_fallback(search_query, item.url)

                if not article_text or len(article_text) < 100:
                    # Provide more detail about fetch failure
                    if not html:
                        item.custom_fields['comments'] = f"Fetch failed: Could not retrieve {item.url[:40]}..."
                    else:
                        item.custom_fields['comments'] = f"Parse failed: No article body extracted (got {len(article_text) if article_text else 0} chars)"
                    print(f"       → {item.custom_fields['comments']}")
                    continue

                comments = []
                found_ecosystem_terms = []
                entities_mentioned = []  # Track all entities for user verification

                # 1. Search for priority ecosystem mentions
                try:
                    mentions = pattern.findall(article_text)
                    if mentions:
                        term_counts = {}
                        for term in mentions:
                            # Handle both string and tuple results from regex
                            if isinstance(term, tuple):
                                term = term[0] if len(term) > 0 else ''
                            if term and isinstance(term, str):
                                term_title = term.strip().title()
                                if term_title:
                                    term_counts[term_title] = term_counts.get(term_title, 0) + 1
                                    found_ecosystem_terms.append(term_title)

                        if term_counts:
                            # Format term counts for display
                            comment_parts = []
                            for term_name, count in term_counts.items():
                                comment_parts.append(f"{term_name} ({count}x)")
                            # Sort by count descending
                            comment_parts.sort(key=lambda x: int(x.split('(')[1].rstrip('x)')), reverse=True)
                            if comment_parts:
                                comments.append(f"Mentions: {', '.join(comment_parts)}")
                except Exception as regex_err:
                    print(f"    [!] Regex error: {regex_err}")

                # 2. Extract entities mentioned in article for user verification
                # This helps users verify if fuzzy matches are correct
                try:
                    entity_patterns = [
                        # Company/project names (capitalized words, often with common suffixes)
                        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:Labs?|Protocol|Network|Finance|Capital|Ventures|Fund|Foundation|Exchange|Wallet|DAO)\b',
                        # Crypto project names (often all caps or CamelCase)
                        r'\b([A-Z]{2,}[a-z]*(?:[A-Z][a-z]*)*)\b',
                        # Common startup naming patterns
                        r'\b([A-Z][a-z]+(?:Fi|Swap|Dex|Pay|Lend|Stake|Mint|Chain|Layer|Bridge|Vault))\b',
                    ]

                    found_entities = set()
                    for ep in entity_patterns:
                        matches = re.findall(ep, article_text[:2000])
                        for m in matches:
                            if isinstance(m, tuple):
                                m = m[0]
                            # Filter out common words and short strings
                            if m and len(m) > 2 and m.lower() not in ['the', 'and', 'for', 'with', 'from', 'that', 'this', 'has', 'have', 'will', 'can', 'are', 'was', 'were', 'been', 'being']:
                                found_entities.add(m)

                    # Filter to meaningful entities (skip very common words)
                    common_words = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
                                   'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                   'September', 'October', 'November', 'December', 'CEO', 'CTO', 'CFO', 'COO'}
                    entities_mentioned = [e for e in found_entities if e not in common_words][:8]  # Limit to 8
                except Exception as ent_err:
                    print(f"    [!] Entity extraction error: {ent_err}")
                    entities_mentioned = []

                # 3. Try Grid matching - first on ecosystem terms found, then on keywords
                if grid_available:
                    article_matcher = GridEntityMatcher()
                    best_match = None

                    # Priority: Match ecosystem terms directly (Solana, Tether, Starknet)
                    for eco_term in set(found_ecosystem_terms):
                        match = article_matcher.match_entity(eco_term, item.url, article_text[:200])
                        if match.matched and match.primary and match.primary.confidence >= 0.7:
                            best_match = match
                            break

                    # Fallback: Try article body keywords
                    if not best_match:
                        article_keywords = article_matcher.extract_keywords(article_text[:500])
                        for kw in article_keywords[:3]:
                            match = article_matcher.match_entity(kw, item.url, article_text[:200])
                            if match.matched and match.primary and match.primary.confidence >= 0.8:
                                best_match = match
                                break

                    # Update Grid fields if we found a match
                    if best_match and best_match.matched:
                        for key, value in best_match.to_dict().items():
                            item.custom_fields[key] = value
                        # Show all matched subjects
                        subjects = ", ".join(m.name for m in best_match.matches[:2])
                        comments.append(f"Grid: {subjects}")

                        # LLM analysis for Grid profile suggestions
                        try:
                            from grid_api import analyze_grid_profile_with_llm
                            primary_match = best_match.primary
                            print(f"       [LLM Debug] primary={primary_match is not None}, text={len(article_text) if article_text else 0}, key={'set' if api_key else 'None'}")
                            if primary_match and article_text and api_key:
                                entity_name = primary_match.name
                                print(f"       [LLM] Analyzing: {entity_name}")
                                # Try to get profile details (works for profiles, may be empty for assets)
                                profile_details = article_matcher.client.get_profile_details(entity_name)
                                # If no profile found, create minimal context from the match
                                if not profile_details.get("profile"):
                                    profile_details = {
                                        "profile": {
                                            "name": entity_name,
                                            "descriptionShort": primary_match.description or f"{primary_match.grid_type}: {entity_name}"
                                        },
                                        "products": [],
                                        "assets": []
                                    }
                                suggestion = analyze_grid_profile_with_llm(article_text, profile_details, api_key=api_key)
                                if suggestion:
                                    comments.append(f"Suggest: {suggestion}")
                                else:
                                    print(f"       [LLM] No suggestion returned")
                            elif not api_key:
                                print(f"       [LLM] Skipped - no API key")
                        except Exception as llm_err:
                            print(f"       [!] LLM error: {llm_err}")
                            pass  # LLM analysis is optional

                # 4. ALWAYS check for USDT/Solana/Starknet support (even with fuzzy matches)
                # Extract context to confirm actual support vs just mentions
                support_findings = []
                support_ecosystems = {
                    'Solana': ['solana', 'sol'],
                    'Starknet': ['starknet', 'strk'],
                    'USDT': ['usdt', 'tether']
                }

                # Positive support indicators
                support_indicators = [
                    r'(?:launch|deploy|build|integrate|support|add|enable|live|available|expand)\w*\s+(?:on|to|for|with)',
                    r'(?:on|to|for|with)\s+\w*\s*(?:launch|deploy|integration|support)',
                    r'(?:native|built|powered)\s+(?:on|by)',
                    r'(?:chain|network|blockchain|ecosystem)',
                    r'(?:wallet|swap|bridge|dex|defi|nft)',
                ]
                support_pattern_str = '|'.join(support_indicators)

                for ecosystem, terms in support_ecosystems.items():
                    term_pattern = '|'.join(re.escape(t) for t in terms)
                    # Find mentions with surrounding context (100 chars before/after)
                    context_pattern = re.compile(
                        r'.{0,100}\b(' + term_pattern + r')\b.{0,100}',
                        re.IGNORECASE | re.DOTALL
                    )

                    matches = context_pattern.findall(article_text)
                    if matches:
                        # Check if any context suggests actual support
                        full_contexts = context_pattern.finditer(article_text)
                        for ctx_match in full_contexts:
                            context = ctx_match.group(0).strip()
                            # Check for support indicators in context
                            if re.search(support_pattern_str, context, re.IGNORECASE):
                                # Clean up the context for display
                                context_clean = ' '.join(context.split())[:150]
                                support_findings.append(f"{ecosystem}: \"{context_clean}...\"")
                                break
                        else:
                            # No strong support indicator, but term was mentioned
                            support_findings.append(f"{ecosystem}: mentioned (verify manually)")

                if support_findings:
                    # Include source URL for reference
                    support_summary = "; ".join(support_findings[:3])  # Limit to 3 ecosystems
                    comments.append(f"Support check [{item.url}]: {support_summary}")

                # 5. Add entities mentioned section for verification
                if entities_mentioned:
                    comments.append(f"Entities: {', '.join(entities_mentioned[:6])}")

                # Combine comments
                if comments:
                    item.custom_fields['comments'] = ' | '.join(comments)
                    print(f"       → {item.custom_fields['comments']}")
                else:
                    item.custom_fields['comments'] = "No relevant mentions"
                    print(f"       → No relevant mentions")

            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                # Include more context in error message
                error_detail = str(e)
                if 'timeout' in error_detail.lower():
                    item.custom_fields['comments'] = f"Timeout: {item.url[:30]}... took too long"
                elif 'connection' in error_detail.lower() or 'refused' in error_detail.lower():
                    item.custom_fields['comments'] = f"Connection error: Could not reach {item.url[:30]}..."
                elif '403' in error_detail or '401' in error_detail:
                    item.custom_fields['comments'] = f"Access denied: {item.url[:30]}... requires auth"
                elif '404' in error_detail:
                    item.custom_fields['comments'] = f"Not found: {item.url[:30]}... may be deleted"
                elif 'unpack' in error_detail.lower():
                    # Log full traceback for debugging tuple unpacking errors
                    print(f"       [DEBUG] Tuple unpack error at: {tb[-500:]}")
                    item.custom_fields['comments'] = f"Parse error: Data format issue in article text"
                else:
                    item.custom_fields['comments'] = f"Research error: {error_detail[:80]}"
                print(f"       → {item.custom_fields['comments']}")

        researched_count = sum(1 for item in items_to_research if 'comments' in item.custom_fields)
        print(f"\n[*] Researched {researched_count}/{len(items_to_research)} articles")

        return items

    def _extract_article_body(self, html: str) -> str:
        """
        Extract only the main article body content, avoiding:
        - Related articles
        - Sidebars
        - Navigation
        - Comments sections
        - Infinite scroll content
        - Footer content
        """
        soup = BeautifulSoup(html, 'lxml')

        # Remove elements that are definitely not article content
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                                   'aside', 'iframe', 'noscript', 'form']):
            tag.decompose()

        # Remove common "related articles" patterns
        related_patterns = [
            'related', 'recommended', 'more-stories', 'more-articles',
            'also-read', 'you-may-like', 'trending', 'popular',
            'sidebar', 'widget', 'advertisement', 'ad-container',
            'social-share', 'comments', 'newsletter', 'subscribe'
        ]

        for pattern in related_patterns:
            # Remove by class
            for tag in soup.find_all(class_=lambda x: x and pattern in x.lower()):
                tag.decompose()
            # Remove by id
            for tag in soup.find_all(id=lambda x: x and pattern in x.lower()):
                tag.decompose()

        # Try to find the main article content using semantic tags
        article_content = None

        # Priority 1: <article> tag
        article_tag = soup.find('article')
        if article_tag:
            article_content = article_tag

        # Priority 2: Common content class names
        if not article_content:
            content_classes = ['article-content', 'article-body', 'post-content',
                              'entry-content', 'story-body', 'article__body',
                              'content-body', 'main-content', 'article-text']
            for cls in content_classes:
                found = soup.find(class_=lambda x: x and cls in str(x).lower())
                if found:
                    article_content = found
                    break

        # Priority 3: <main> tag
        if not article_content:
            main_tag = soup.find('main')
            if main_tag:
                article_content = main_tag

        # Priority 4: Largest <div> with significant text (heuristic)
        if not article_content:
            article_content = soup.body if soup.body else soup

        # Extract text from the identified content
        if article_content:
            # Get text with proper spacing
            text = article_content.get_text(separator=' ', strip=True)

            # Clean up excessive whitespace
            text = ' '.join(text.split())

            # Limit to reasonable article length (avoid infinite scroll content)
            # Most articles are under 10000 characters
            return text[:10000]

        return ""

    def deduplicate_csv(self, csv_path: str, key_column: str = 'url') -> int:
        """Remove duplicates from CSV file."""
        return self.csv_manager.deduplicate(csv_path, key_column)


# =============================================================================
# CUSTOM INSTRUCTIONS LOADER
# =============================================================================

def load_custom_instructions(path: str) -> Dict:
    """
    Load custom extraction instructions from JSON file.

    Expected format:
    {
        "include_patterns": ["crypto", "bitcoin", "ethereum"],
        "exclude_patterns": ["sponsor", "advertisement", "subscribe"],
        "allowed_domains": [],  // Empty = all allowed
        "blocked_domains": ["twitter.com", "facebook.com", "linkedin.com"],
        "csv_columns": ["title", "url", "category", "source_name", "date_published"]
    }
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading custom instructions: {e}")
        return {}


def save_custom_instructions(instructions: Dict, path: str):
    """Save custom instructions to JSON file."""
    with open(path, 'w') as f:
        json.dump(instructions, f, indent=2)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Command-line interface for the data CSV processor."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract links and data from web sources into CSV format.'
    )
    parser.add_argument('urls', nargs='+', help='URLs to process')
    parser.add_argument('-o', '--output', default='extracted_data.csv',
                        help='Output CSV file path')
    parser.add_argument('-c', '--config', help='Path to custom instructions JSON file')
    parser.add_argument('--no-redirects', action='store_true',
                        help='Skip redirect resolution')
    parser.add_argument('--no-clean', action='store_true',
                        help='Keep tracking parameters in URLs')
    parser.add_argument('--no-append', action='store_true',
                        help='Overwrite CSV instead of appending')
    parser.add_argument('--dedupe', action='store_true',
                        help='Remove duplicates after processing')
    parser.add_argument('--columns', nargs='+',
                        help='Custom CSV columns (space-separated)')

    args = parser.parse_args()

    # Build config
    config = ExtractionConfig(
        resolve_redirects=not args.no_redirects,
        strip_tracking_params=not args.no_clean,
        append_mode=not args.no_append,
    )

    if args.columns:
        config.csv_columns = args.columns

    # Load custom instructions if provided
    custom_instructions = None
    if args.config:
        custom_instructions = load_custom_instructions(args.config)

    # Process URLs
    processor = DataCSVProcessor(config)
    items = processor.process_urls(args.urls, custom_instructions)

    # Save to CSV
    if items:
        processor.save_to_csv(items, args.output)

        if args.dedupe:
            processor.deduplicate_csv(args.output)

        print(f"\n✓ Done! Output saved to: {args.output}")
    else:
        print("\n✗ No items extracted.")


if __name__ == "__main__":
    main()
