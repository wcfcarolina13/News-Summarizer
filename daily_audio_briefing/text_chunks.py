"""Boundary-aware text splitting shared by the article map-reduce summarizer
(source_fetcher) and chunked cleaning (audio_jobs). Stdlib only."""
from typing import List


def split_text(text: str, size: int) -> List[str]:
    """Split text into chunks of at most `size` chars, preferring paragraph, then
    line, then sentence boundaries so a chunk never starts mid-sentence."""
    if len(text) <= size:
        return [text]
    chunks, start, n = [], 0, len(text)
    while start < n:
        if n - start <= size:
            chunks.append(text[start:].strip())
            break
        window = text[start:start + size]
        floor = int(size * 0.8)
        cut = -1
        for sep, keep in (("\n\n", 0), ("\n", 0), (". ", 1)):
            pos = window.rfind(sep)
            if pos >= floor:
                cut = pos + keep
                break
        if cut < 0:
            cut = size
        chunks.append(text[start:start + cut].strip())
        start += cut
    return [c for c in chunks if c]
