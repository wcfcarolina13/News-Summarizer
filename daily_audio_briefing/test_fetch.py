#!/usr/bin/env python3
"""Test script to debug article fetching."""

import requests
from bs4 import BeautifulSoup
import re

def fetch_article_content(url: str) -> str:
    """Fetch and extract article body from URL."""
    try:
        # Browser headers - NOTE: Don't request compressed encoding, let requests handle it
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            # Don't set Accept-Encoding - let requests library handle decompression automatically
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        html = None
        content_type = None

        # Try with requests session (handles cookies)
        try:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
            print(f"  Content-Type: {content_type}")

            # Check for non-HTML content
            if content_type and not any(ct in content_type for ct in ['text/html', 'text/plain', 'application/xhtml']):
                print(f"  ERROR: Non-HTML content-type")
                return ""

            # Use proper encoding
            if response.encoding:
                html = response.text
            else:
                html = response.content.decode('utf-8', errors='ignore')
            print(f"  HTTP {response.status_code}, {len(html)} bytes")
        except Exception as e:
            print(f"  Requests failed: {e}")
            return ""

        if not html:
            return ""

        # Try lxml first, fallback to html.parser
        soup = None
        try:
            soup = BeautifulSoup(html, 'lxml')
            print(f"  Parsed with lxml")
        except Exception as e:
            print(f"  lxml failed: {e}, trying html.parser")
            try:
                soup = BeautifulSoup(html, 'html.parser')
                print(f"  Parsed with html.parser")
            except Exception as e2:
                print(f"  html.parser also failed: {e2}")
                return ""

        if soup is None:
            return ""

        # Remove junk elements
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                                   'aside', 'iframe', 'noscript', 'form', 'button', 'svg']):
            tag.decompose()

        article_text = None

        # Platform-specific extraction - Substack
        is_substack = 'substack.com' in url or 'experimental-history.com' in url
        if not is_substack:
            is_substack = (
                soup.find('div', class_='available-content') is not None or
                soup.find('div', class_='body markup') is not None
            )

        if is_substack:
            print(f"  Detected as Substack")
            substack_selectors = [
                'div.body.markup',
                'div.body-markup',
                'div.available-content',
                'div.post-content',
                'div.post-content-final',
                'div.body',
                'div.markup',
                'article.post',
                'article',
                '.post-content',
                '.body.markup',
            ]
            for selector in substack_selectors:
                try:
                    content = soup.select_one(selector)
                    if content:
                        text = content.get_text(separator='\n', strip=True)
                        if len(text) > 200:
                            article_text = text
                            print(f"  Substack: found {len(text)} chars with '{selector}'")
                            break
                except Exception:
                    continue

        # Generic selectors
        if not article_text or len(article_text) < 200:
            selectors = [
                'article',
                'div.article-content',
                'div.article-body',
                'div.post-content',
                'div.entry-content',
                'main',
                '[role="main"]',
                '[role="article"]',
                'div.content',
            ]
            for selector in selectors:
                try:
                    content = soup.select_one(selector)
                    if content:
                        text = content.get_text(separator='\n', strip=True)
                        if len(text) > 200:
                            article_text = text
                            print(f"  Generic: found {len(text)} chars with '{selector}'")
                            break
                except Exception:
                    continue

        # Fallback: largest div with paragraphs
        if not article_text or len(article_text) < 200:
            all_divs = soup.find_all(['div', 'article', 'section', 'main'])
            best_text = ""
            best_source = ""
            for div in all_divs:
                paragraphs = div.find_all('p')
                if len(paragraphs) >= 3:
                    text = div.get_text(separator='\n', strip=True)
                    if len(text) > len(best_text):
                        best_text = text
                        best_source = f"{div.name}.{div.get('class', [''])[0] if div.get('class') else ''}"
            if best_text and len(best_text) > 200:
                article_text = best_text
                print(f"  Fallback: found {len(best_text)} chars from '{best_source}'")

        # Last resort: body text
        if not article_text or len(article_text) < 200:
            if soup.body:
                body_text = soup.body.get_text(separator='\n', strip=True)
                if len(body_text) > 500:
                    article_text = body_text
                    print(f"  Last resort: body text ({len(body_text)} chars)")

        if not article_text:
            print(f"  ERROR: No content found")
            return ""

        # Clean up
        # Remove non-printable characters
        cleaned = []
        for char in article_text:
            if char.isprintable() or char in '\n\t\r':
                cleaned.append(char)
            elif ord(char) > 127:
                cleaned.append(' ')
        article_text = ''.join(cleaned)

        # Remove excessive whitespace
        article_text = re.sub(r'\n{3,}', '\n\n', article_text)
        article_text = re.sub(r' {3,}', ' ', article_text)

        # Check word quality
        words = article_text.split()
        if words:
            real_words = sum(1 for w in words if sum(c.isalpha() for c in w) > len(w) * 0.5)
            word_ratio = real_words / len(words)
            print(f"  Word quality: {word_ratio:.1%} real words")
            if word_ratio < 0.5:
                print(f"  WARNING: Low word quality, filtering...")
                clean_lines = []
                for line in article_text.split('\n'):
                    line = line.strip()
                    if len(line) < 10:
                        continue
                    line_words = line.split()
                    if line_words:
                        line_real = sum(1 for w in line_words if sum(c.isalpha() for c in w) > len(w) * 0.5)
                        if line_real / len(line_words) > 0.6:
                            clean_lines.append(line)
                if clean_lines:
                    article_text = '\n'.join(clean_lines)
                    print(f"  Filtered to {len(article_text)} chars")

        final_text = article_text.strip()
        print(f"  Final: {len(final_text)} chars")

        # Show first 300 chars as preview
        preview = final_text[:300].replace('\n', ' ')
        print(f"  Preview: {preview}...")

        return final_text

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ""


def main():
    urls = [
        "https://squareman.substack.com/p/people-are-tired-of-innovation",
        "https://www.spectramarkets.com/amfx/lets-assume-zero/",
        "https://www.deeplearning.ai/the-batch/issue-333/",  # Fixed URL
        "https://www.experimental-history.com/p/so-you-wanna-de-bog-yourself",  # Fixed URL
    ]

    print("=" * 60)
    print("ARTICLE FETCH TEST")
    print("=" * 60)

    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/4] {url[:60]}...")
        content = fetch_article_content(url)
        results.append({
            'url': url,
            'success': len(content) > 100,
            'length': len(content),
            'preview': content[:200] if content else ""
        })

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        status = "✓" if r['success'] else "✗"
        print(f"{status} [{i}] {r['length']:,} chars - {r['url'][:50]}...")


if __name__ == "__main__":
    main()
