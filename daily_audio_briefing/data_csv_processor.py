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
        pub_date = self._extract_date(soup)

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

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date."""
        # Try meta tags
        date_meta = soup.find('meta', property='article:published_time')
        if date_meta:
            return date_meta.get('content', '')[:10]

        # Try time elements
        time_elem = soup.find('time')
        if time_elem:
            return time_elem.get('datetime', time_elem.get_text(strip=True))[:10]

        return datetime.now().strftime('%Y-%m-%d')

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

        columns = custom_columns or self.config.csv_columns

        # Check for custom fields and add them to columns
        all_custom_fields = set()
        for item in items:
            all_custom_fields.update(item.custom_fields.keys())

        # Add custom fields to columns if not already present
        for field in all_custom_fields:
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

            for item in items:
                row = item.to_dict()
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
        # Method 1: Try requests first
        try:
            response = requests.get(
                url,
                headers={'User-Agent': self.config.user_agent},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    [!] requests failed: {e}")

        # Method 2: Try urllib with custom SSL context
        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.config.user_agent})
            if SSL_CONTEXT:
                with urllib.request.urlopen(req, timeout=self.config.timeout, context=SSL_CONTEXT) as response:
                    return response.read().decode('utf-8', errors='ignore')
            else:
                with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                    return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"    [!] urllib failed: {e}")

        # Method 3: Try with no SSL verification (last resort)
        try:
            import ssl
            no_verify_ctx = ssl.create_default_context()
            no_verify_ctx.check_hostname = False
            no_verify_ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': self.config.user_agent})
            with urllib.request.urlopen(req, timeout=self.config.timeout, context=no_verify_ctx) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"    [!] All fetch methods failed for {url}: {e}")
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
