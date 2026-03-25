# Source Generated with Decompyle++
# File: data_csv_processor.pyc (Python 3.12)

__doc__ = '\nData CSV Processor - Extract links and data from various sources into CSV format.\n\nSupports:\n- Newsletters (beehiiv, Substack, etc.)\n- Articles\n- RSS Feeds\n- YouTube videos\n- Generic web pages\n\nFeatures:\n- Resolves redirect URLs (beehiiv tracking links)\n- Strips tracking parameters (utm_*, etc.)\n- Custom extraction rules per source/domain\n- Appends to existing CSV sheets\n'
import csv
import os
import re
import json
import ssl
import urllib.request as urllib
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.set_ciphers('DEFAULT@SECLEVEL=1')
ExtractedItem = <NODE:12>()
ExtractionConfig = <NODE:12>()

class URLProcessor:
    '''Handles URL cleaning, redirect resolution, and parameter stripping.'''
    
    def __init__(self = None, config = None):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent })
        self._redirect_cache = { }

    
    def clean_url(self = None, url = None):
        '''Strip tracking parameters from URL.'''
        if not self.config.strip_tracking_params:
            return url
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values = True)
    # WARNING: Decompyle incomplete

    
    def resolve_redirect(self = None, url = None):
        '''Follow redirects to get final destination URL.'''
        if not self.config.resolve_redirects:
            return url
        if None in self._redirect_cache:
            return self._redirect_cache[url]
        response = self.session.head(url, allow_redirects = True, timeout = self.config.timeout)
        final_url = response.url
        if response.status_code >= 400:
            response = self.session.get(url, allow_redirects = True, timeout = self.config.timeout)
            final_url = response.url
        self._redirect_cache[url] = final_url
        return final_url
    # WARNING: Decompyle incomplete

    
    def process_url(self = None, url = None):
        '''
        Process URL: resolve redirects and clean parameters.
        Returns (cleaned_url, original_url).
        '''
        original = url
        resolved = self.resolve_redirect(url)
        cleaned = self.clean_url(resolved)
        return (cleaned, original)

    
    def is_internal_link(self = None, url = None, base_domain = None):
        '''Check if URL is internal to the base domain.'''
        parsed = urlparse(url)
        return base_domain in parsed.netloc
    # WARNING: Decompyle incomplete

    
    def normalize_url(self = None, url = None, base_url = None):
        '''Convert relative URLs to absolute.'''
        if url.startswith('http'):
            return url
        if None.startswith('//'):
            return 'https:' + url
        if None.startswith('/'):
            parsed = urlparse(base_url)
            return f'''{parsed.scheme}://{parsed.netloc}{url}'''
        return None.rstrip('/') + '/' + url



class BaseExtractor:
    '''Base class for source-specific extractors.'''
    name = 'base'
    supported_domains: List[str] = []
    
    def __init__(self = None, url_processor = None, config = None):
        self.url_processor = url_processor
        self.config = config

    
    def can_handle(self = None, url = None):
        '''Check if this extractor can handle the given URL.'''
        pass
    # WARNING: Decompyle incomplete

    
    def preprocess_url(self = None, url = None):
        '''Preprocess URL before fetching. Override in subclasses if needed.'''
        return url

    
    def extract(self = None, url = None, html = None, custom_instructions = (None,)):
        '''Extract items from the source. Override in subclasses.'''
        raise NotImplementedError

    
    def _get_soup(self = None, html = None):
        '''Parse HTML with BeautifulSoup.'''
        return BeautifulSoup(html, 'html.parser')



class BeehiivExtractor(BaseExtractor):
    '''Extractor for Beehiiv newsletters (like CryptoSum).'''
    name = 'beehiiv'
    supported_domains = [
        'beehiiv.com']
    
    def _find_latest_post_url(self = None, archive_html = None, base_url = None):
        '''Given a beehiiv archive/homepage HTML, find the URL of the latest newsletter post.'''
        soup = BeautifulSoup(archive_html, 'html.parser')
        parsed_base = urlparse(base_url)
        base_domain = f'''{parsed_base.scheme}://{parsed_base.netloc}'''
        for a_tag in soup.find_all('a', href = True):
            href = a_tag['href']
            if not '/p/' in href:
                continue
            if href.startswith('/'):
                
                return soup.find_all('a', href = True), base_domain + href
            if not soup.find_all('a', href = True).startswith('http'):
                continue
            
            return None, href
        return ''

    
    def preprocess_url(self = None, url = None):
        '''If given a beehiiv homepage/archive, find and return the latest post URL.'''
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if '/p/' in path:
            return url
        None('    [Beehiiv] Archive page detected, finding latest newsletter post...')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml' }
        resp = requests.get(url, headers = headers, timeout = 15)
        resp.raise_for_status()
        latest_url = self._find_latest_post_url(resp.text, url)
        if latest_url:
            print(f'''    [Beehiiv] Latest post: {latest_url[:80]}...''')
            return latest_url
        None('    [Beehiiv] No posts found on archive page, using original URL')
        return url
    # WARNING: Decompyle incomplete

    
    def get_archive_posts(self = None, base_url = None, since_date = None, on_progress = (None, None)):
        '''
        Crawl the beehiiv archive and return all post URLs with dates.

        Args:
            base_url: The beehiiv newsletter base URL (e.g. https://cryptosum.beehiiv.com)
            since_date: Only return posts on or after this date (YYYY-MM-DD). None = all posts.
            on_progress: Optional callback(message) for progress updates.

        Returns:
            List of dicts: [{"url": "https://...", "date": "2026-02-20"}, ...]
            Ordered oldest-first for chronological processing.
        '''
        import time as _time
        parsed = urlparse(base_url)
        base_domain = f'''{parsed.scheme}://{parsed.netloc}'''
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml' }
        all_posts = []
        seen_slugs = set()
        page = 0
        stop_crawling = False
    # WARNING: Decompyle incomplete

    
    def extract(self = None, url = None, html = None, custom_instructions = (None,)):
        '''Extract all links and topics from a Beehiiv newsletter.'''
        soup = self._get_soup(html)
        items = []
        seen_urls = set()
        source_name = self._extract_source_name(soup, url)
        pub_date = self._extract_date(soup, url)
        if not soup.find('div', class_ = 'post-content'):
            soup.find('div', class_ = 'post-content')
            if not soup.find('article'):
                soup.find('article')
        content_area = soup.body
        if not content_area:
            return items
        current_category = None
        for element in content_area.find_all([
            'h1',
            'h2',
            'h3',
            'h4',
            'p',
            'li']):
            if element.name in ('h1', 'h2', 'h3', 'h4'):
                header_text = element.get_text(strip = True)
                if header_text and len(header_text) < 100:
                    current_category = header_text
                continue
            links = element.find_all('a', href = True)
            for link in links:
                href = link.get('href', '')
                if href and href.startswith('#') or href.startswith('mailto:'):
                    continue
                if self._is_internal_link(href, url):
                    continue
                link_text = link.get_text(strip = True)
                context = self._get_link_context(link, element)
                original_url = href
                if 'links.beehiiv.com' in href or 'beehiiv.com/r/' in href:
                    extracted_dest = self._extract_beehiiv_dest(href)
                    if extracted_dest:
                        href = extracted_dest
                (cleaned_url, _) = self.url_processor.process_url(href)
                if cleaned_url in seen_urls:
                    continue
                seen_urls.add(cleaned_url)
                if not custom_instructions and self._passes_filter(cleaned_url, link_text, context, current_category, custom_instructions):
                    continue
                if not link_text:
                    link_text
                item = ExtractedItem(title = self._extract_title_from_url(cleaned_url), url = cleaned_url, original_url = original_url, source_name = source_name, source_url = url, category = current_category, description = context, date_published = pub_date)
                if custom_instructions and 'custom_fields' in custom_instructions:
                    for field_name, extractor_func in custom_instructions['custom_fields'].items():
                        item.custom_fields[field_name] = extractor_func(link, element, soup)
                items.append(item)
        return items
    # WARNING: Decompyle incomplete

    
    def _extract_source_name(self = None, soup = None, url = None):
        '''Extract the newsletter/publication name.'''
        og_site = soup.find('meta', property = 'og:site_name')
        if og_site:
            return og_site.get('content', '')
        title = None.find('title')
        if title:
            return title.get_text(strip = True).split('|')[0].strip()
        parsed = None(url)
        return parsed.netloc.split('.')[0].title()

    
    def _extract_date(self = None, soup = None, url = None):
        '''Extract publication date from newsletter.'''
        date_meta = soup.find('meta', property = 'article:published_time')
    # WARNING: Decompyle incomplete

    
    def _is_internal_link(self = None, href = None, source_url = None):
        '''Check if link is internal to the newsletter platform.'''
        pass
    # WARNING: Decompyle incomplete

    
    def _extract_beehiiv_dest(self = None, url = None):
        '''Extract destination URL from beehiiv redirect link.'''
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'dest' in query_params:
            return query_params['dest'][0]
        if None in query_params:
            return query_params['url'][0]
        for key, values in None.items():
            for val in values:
                if not val.startswith('http'):
                    continue
                
                
                return None.items(), values, val
        return ''
    # WARNING: Decompyle incomplete

    
    def _get_link_context(self = None, link = None, parent_element = None):
        '''Get the text context around a link.'''
        if parent_element and parent_element != link:
            text = parent_element.get_text(separator = ' ', strip = True)
            text = ' '.join(text.split())
            return text[:200]

    
    def _extract_title_from_url(self = None, url = None):
        '''Extract a title from URL path if no link text.'''
        parsed = urlparse(url)
        path = parsed.path.strip('/').split('/')[-1]
        return path.replace('-', ' ').replace('_', ' ').title()[:100]

    
    def _passes_filter(self, url, text = None, context = None, category = None, instructions = ('url', str, 'text', str, 'context', str, 'category', str, 'instructions', Dict, 'return', bool)):
        '''Check if item passes custom instruction filters.'''
        pass
    # WARNING: Decompyle incomplete



class GenericWebExtractor(BaseExtractor):
    '''Generic extractor for any web page.'''
    name = 'generic'
    supported_domains = []
    
    def can_handle(self = None, url = None):
        '''Generic extractor handles any URL.'''
        return True

    
    def extract(self = None, url = None, html = None, custom_instructions = (None,)):
        '''Extract all external links from a web page.'''
        soup = self._get_soup(html)
        items = []
        source_name = self._extract_source_name(soup, url)
        parsed_source = urlparse(url)
        for link in soup.find_all('a', href = True):
            href = link.get('href', '')
            if href and href.startswith('#') or href.startswith('mailto:'):
                continue
            full_url = self.url_processor.normalize_url(href, url)
            parsed = urlparse(full_url)
            if parsed.netloc == parsed_source.netloc:
                continue
            (cleaned_url, original_url) = self.url_processor.process_url(full_url)
            link_text = link.get_text(strip = True)
            if not link_text:
                link_text
            item = ExtractedItem(title = self._extract_title_from_url(cleaned_url), url = cleaned_url, original_url = original_url, source_name = source_name, source_url = url, category = 'External Link')
            items.append(item)
        return items

    
    def _extract_source_name(self = None, soup = None, url = None):
        '''Extract page/site name.'''
        og_site = soup.find('meta', property = 'og:site_name')
        if og_site:
            return og_site.get('content', '')
        title = None.find('title')
        if title:
            return title.get_text(strip = True)[:50]
        return None(url).netloc

    
    def _extract_title_from_url(self = None, url = None):
        '''Extract title from URL.'''
        parsed = urlparse(url)
        path = parsed.path.strip('/').split('/')[-1]
        if not path.replace('-', ' ').replace('_', ' ').title()[:100]:
            path.replace('-', ' ').replace('_', ' ').title()[:100]
        return parsed.netloc



class RSSExtractor(BaseExtractor):
    '''Extractor for RSS/Atom feeds.'''
    name = 'rss'
    supported_domains = []
    
    def can_handle(self = None, url = None):
        '''Check if URL is an RSS feed.'''
        pass
    # WARNING: Decompyle incomplete

    
    def extract(self = None, url = None, html = None, custom_instructions = (None,)):
        '''Extract items from RSS feed.'''
        soup = BeautifulSoup(html, 'xml')
        items = []
        feed_title = soup.find('title')
        source_name = feed_title.get_text(strip = True) if feed_title else urlparse(url).netloc
        if not soup.find_all('item'):
            soup.find_all('item')
        entries = soup.find_all('entry')
        for entry in entries:
            title_elem = entry.find('title')
            link_elem = entry.find('link')
            if not entry.find('description'):
                entry.find('description')
                if not entry.find('summary'):
                    entry.find('summary')
            desc_elem = entry.find('content')
            if not entry.find('pubDate'):
                entry.find('pubDate')
                if not entry.find('published'):
                    entry.find('published')
            date_elem = entry.find('updated')
            if not entry.find('author'):
                entry.find('author')
            author_elem = entry.find('dc:creator')
            if link_elem:
                if not link_elem.get('href'):
                    link_elem.get('href')
                link_url = link_elem.get_text(strip = True)
            
            (cleaned_url, original_url) = self.url_processor.process_url(link_url)
            item = ExtractedItem(title = title_elem.get_text(strip = True) if title_elem else '', url = cleaned_url, original_url = original_url, source_name = source_name, source_url = url, category = 'RSS Feed', description = desc_elem.get_text(strip = True)[:500] if desc_elem else '', date_published = date_elem.get_text(strip = True) if date_elem else '', author = author_elem.get_text(strip = True) if author_elem else '')
            items.append(item)
        return items



class TelegramExtractor(BaseExtractor):
    '''Extractor for Telegram channel preview pages.'''
    name = 'telegram'
    supported_domains = [
        't.me']
    
    def can_handle(self = None, url = None):
        '''Check if URL is a Telegram channel.'''
        parsed = urlparse(url)
        return parsed.netloc == 't.me'

    
    def preprocess_url(self = None, url = None):
        '''Convert t.me/channel to t.me/s/channel preview format.'''
        parsed = urlparse(url)
        if parsed.netloc == 't.me' and '/s/' not in parsed.path:
            channel = parsed.path.strip('/')
            return f'''https://t.me/s/{channel}'''

    
    def _is_article_url(self = None, url = None):
        '''Check if URL looks like an article (not a homepage).'''
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if bool(path):
            bool(path)
        if not '/' in path:
            '/' in path
        return len(path) > 20

    
    def _select_best_link(self = None, links = None):
        '''Select the best link from a list (prefer article URLs over homepages).'''
        pass
    # WARNING: Decompyle incomplete

    
    def extract(self = None, url = None, html = None, custom_instructions = (None,)):
        '''Extract items from Telegram channel preview page.'''
        soup = self._get_soup(html)
        items = []
        seen_urls = set()
        channel_title = soup.find('div', class_ = 'tgme_channel_info_header_title')
        source_name = channel_title.get_text(strip = True) if channel_title else 'Telegram Channel'
        messages = soup.find_all('div', class_ = 'tgme_widget_message_wrap')
        for msg in messages:
            text_div = msg.find('div', class_ = 'tgme_widget_message_text')
            if not text_div:
                continue
            message_text = text_div.get_text(strip = True)
            if not message_text:
                continue
            time_elem = msg.find('time')
            date_published = time_elem.get('datetime', '') if time_elem else ''
            links = text_div.find_all('a', href = True)
            external_links = []
            for link in links:
                href = link.get('href', '')
                if not href:
                    continue
                if not href.startswith('http'):
                    continue
                if not 't.me' not in href:
                    continue
                external_links.append(href)
            if external_links:
                best_link = self._select_best_link(external_links)
                if not best_link:
                    continue
                (cleaned_url, original_url) = self.url_processor.process_url(best_link)
                if cleaned_url in seen_urls:
                    continue
                seen_urls.add(cleaned_url)
                title = message_text
                item = ExtractedItem(title = title, url = cleaned_url, original_url = original_url, source_name = source_name, source_url = url, category = 'Telegram', description = '', date_published = date_published)
                items.append(item)
                continue
            msg_link = msg.find('a', class_ = 'tgme_widget_message_date')
            msg_url = msg_link.get('href', url) if msg_link else url
            if msg_url in seen_urls:
                continue
            seen_urls.add(msg_url)
            title = message_text
            item = ExtractedItem(title = title, url = msg_url, original_url = msg_url, source_name = source_name, source_url = url, category = 'Telegram', description = '', date_published = date_published)
            items.append(item)
        return items



class CSVManager:
    '''Handles CSV file operations with append support.'''
    
    def __init__(self = None, config = None):
        self.config = config

    
    def write_items(self = None, items = None, output_path = None, custom_columns = (None,)):
