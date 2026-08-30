"""
Search result snippets — a window of page text centered on the first
matching query term, the way Google/Bing-style results show context
around your search words instead of just a title.

Takes the already-tokenized (stemmed) query terms, the same ones used
to build the index — this works well in practice because Porter
stemming mostly just removes suffixes, so a stem like "crawl" is
naturally a substring of "crawler", "crawling", "crawled", etc.,
letting one stemmed term match several real word forms in the raw text.
"""

import re

SNIPPET_RADIUS = 100  # characters shown on each side of the first match


def make_snippet(text: str, terms: list[str]) -> str:
    """Find the first occurrence of any query term in the raw page text
    and return a short window around it, with ellipses if truncated.
    Falls back to the start of the text if no term is found there
    (e.g. it only matched via stemming, not the literal substring).
    """
    if not text:
        return ""

    lower_text = text.lower()
    first_index = None
    for term in terms:
        idx = lower_text.find(term.lower())
        if idx != -1 and (first_index is None or idx < first_index):
            first_index = idx

    if first_index is None:
        snippet = text[: SNIPPET_RADIUS * 2]
        suffix = "…" if len(text) > len(snippet) else ""
        return snippet.strip() + suffix

    start = max(0, first_index - SNIPPET_RADIUS)
    end = min(len(text), first_index + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix
