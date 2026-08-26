"""
Day 3 — Tokenizer

Turns raw page text into a clean list of index-ready terms:
  1. Lowercase everything (so "Search" and "search" are the same term)
  2. Strip punctuation / non-alphanumeric characters
  3. Split on whitespace
  4. Drop stopwords (common words like "the", "is", "and" that carry
     little search value and would otherwise dominate every index entry)
  5. Stem each remaining word (Porter stemmer) so "running", "runs",
     and "ran"-adjacent forms collapse toward a shared root, improving
     recall (e.g. searching "run" also matches pages saying "running")

We use nltk's PorterStemmer directly — it's a pure rule-based
algorithm bundled with nltk, so unlike stopword corpora it needs
no separate download step and works offline out of the box.
Our stopword list is hardcoded below for the same reason: it keeps
setup to "pip install" only, no nltk.download() step that could fail
on a machine without internet access at that moment.
"""

import re
from nltk.stem import PorterStemmer

_stemmer = PorterStemmer()

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to",
    "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "once", "here", "there", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now", "is", "am", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "would", "could", "of", "it", "its",
    "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "what", "which", "who", "whom", "as", "until", "while",
}

_token_pattern = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    """Raw text -> list of stemmed, stopword-filtered lowercase terms."""
    if not text:
        return []
    raw_tokens = _token_pattern.findall(text.lower())
    return [
        _stemmer.stem(tok)
        for tok in raw_tokens
        if tok not in STOPWORDS and len(tok) > 1
    ]