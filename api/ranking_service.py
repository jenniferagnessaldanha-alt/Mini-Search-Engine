"""
Day 5 — Ranking logic used by the API.

This mirrors ranking/tfidf.py and ranking/pagerank.py, kept as a
self-contained copy inside the api/ package. We do this deliberately
rather than importing across folders: crawler/, indexer/, and ranking/
each already have their own storage.py with the same module name, and
Python can only have one "storage" module loaded at a time on a given
sys.path — importing across folders risks one silently shadowing
another. Keeping each top-level folder self-contained avoids that
whole class of bug, at the small cost of some duplicated code.
"""

import math
from collections import defaultdict

from .storage import get_connection


# ---- TF-IDF ----------------------------------------------------------

def _total_document_count() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pages;")
            return cur.fetchone()[0]


def _document_frequency(term: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT doc_id) FROM inverted_index WHERE term = %s;", (term,))
            return cur.fetchone()[0]


def _term_frequencies(term: str) -> dict[int, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT doc_id, frequency FROM inverted_index WHERE term = %s;", (term,))
            return dict(cur.fetchall())


def tfidf_scores(terms: list[str]) -> dict[int, float]:
    n_docs = _total_document_count()
    if n_docs == 0:
        return {}
    scores: dict[int, float] = defaultdict(float)
    for term in terms:
        df = _document_frequency(term)
        if df == 0:
            continue
        idf = max(0.0, math.log(n_docs / (1 + df)))  # never let a matching term subtract from the score
        for doc_id, tf in _term_frequencies(term).items():
            scores[doc_id] += tf * idf
    return dict(scores)


# ---- PageRank ----------------------------------------------------------

DAMPING = 0.85
ITERATIONS = 30
CONVERGENCE_THRESHOLD = 1e-6


def _load_graph():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, url FROM pages;")
            rows = cur.fetchall()
            url_to_id = {url: doc_id for doc_id, url in rows}
            doc_ids = list(url_to_id.values())

            cur.execute("SELECT from_doc_id, to_url FROM links;")
            link_rows = cur.fetchall()

    outgoing = defaultdict(list)
    for from_id, to_url in link_rows:
        to_id = url_to_id.get(to_url)
        if to_id is not None and to_id != from_id:
            outgoing[from_id].append(to_id)

    return doc_ids, outgoing


def compute_pagerank() -> dict[int, float]:
    doc_ids, outgoing = _load_graph()
    n = len(doc_ids)
    if n == 0:
        return {}

    pr = {doc_id: 1.0 / n for doc_id in doc_ids}
    incoming = defaultdict(list)
    for from_id, targets in outgoing.items():
        for to_id in targets:
            incoming[to_id].append(from_id)
    out_degree = {doc_id: len(outgoing.get(doc_id, [])) for doc_id in doc_ids}

    for _ in range(ITERATIONS):
        new_pr = {}
        dangling_sum = sum(pr[d] for d in doc_ids if out_degree[d] == 0)
        for doc_id in doc_ids:
            incoming_score = sum(
                pr[q] / out_degree[q] for q in incoming.get(doc_id, []) if out_degree[q] > 0
            )
            new_pr[doc_id] = (1 - DAMPING) / n + DAMPING * (incoming_score + dangling_sum / n)
        diff = sum(abs(new_pr[d] - pr[d]) for d in doc_ids)
        pr = new_pr
        if diff < CONVERGENCE_THRESHOLD:
            break

    return pr


# ---- Combined ranking ----------------------------------------------------

def _normalize(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    max_val = max(scores.values())
    if max_val == 0:
        return {doc_id: 0.0 for doc_id in scores}
    return {doc_id: value / max_val for doc_id, value in scores.items()}


def rank(terms: list[str], tfidf_weight: float = 0.7, pagerank_weight: float = 0.3) -> list[dict]:
    raw_tfidf = tfidf_scores(terms)
    if not raw_tfidf:
        return []

    pagerank_all = compute_pagerank()

    norm_tfidf = _normalize(raw_tfidf)
    candidate_pagerank = {doc_id: pagerank_all.get(doc_id, 0.0) for doc_id in raw_tfidf}
    norm_pagerank = _normalize(candidate_pagerank)

    combined = {
        doc_id: tfidf_weight * norm_tfidf.get(doc_id, 0.0) + pagerank_weight * norm_pagerank.get(doc_id, 0.0)
        for doc_id in raw_tfidf
    }

    ranked_ids = sorted(combined.keys(), key=lambda d: combined[d], reverse=True)
    return [
        {
            "doc_id": doc_id,
            "score": round(combined[doc_id], 4),
            "tfidf": round(raw_tfidf.get(doc_id, 0.0), 4),
            "pagerank": round(pagerank_all.get(doc_id, 0.0), 6),
        }
        for doc_id in ranked_ids
    ]