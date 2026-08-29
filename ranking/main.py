# TODO: Day 4 - TF-IDF + PageRank
"""
Day 4 — Combined Ranking Engine

Final score = TF-IDF relevance blended with PageRank importance.
Both are normalized to 0-1 before weighting so one doesn't silently
dominate the other.

Usage
-----
    python ranking/main.py --query "web crawler"
    python ranking/main.py --query "web crawler" --tfidf-weight 0.8 --pagerank-weight 0.2
"""

import argparse
import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "indexer"))
from tokenizer import tokenize  # noqa: E402

from tfidf import tfidf_scores
from pagerank import compute_pagerank
from storage import get_pages_by_ids


def _normalize(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    max_val = max(scores.values())
    if max_val == 0:
        return {doc_id: 0.0 for doc_id in scores}
    return {doc_id: value / max_val for doc_id, value in scores.items()}


def rank(query: str, tfidf_weight: float = 0.7, pagerank_weight: float = 0.3) -> list[dict]:
    terms = tokenize(query)
    if not terms:
        return []

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
    pages = {p["id"]: p for p in get_pages_by_ids(ranked_ids)}

    results = []
    for doc_id in ranked_ids:
        page = pages.get(doc_id)
        if page:
            results.append({
                "url": page["url"],
                "title": page["title"],
                "score": round(combined[doc_id], 4),
                "tfidf": round(raw_tfidf.get(doc_id, 0.0), 4),
                "pagerank": round(pagerank_all.get(doc_id, 0.0), 6),
            })
    return results


def parse_args():
    p = argparse.ArgumentParser(description="Day 4: ranked search (TF-IDF + PageRank)")
    p.add_argument("--query", required=True)
    p.add_argument("--tfidf-weight", type=float, default=0.7)
    p.add_argument("--pagerank-weight", type=float, default=0.3)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    results = rank(args.query, args.tfidf_weight, args.pagerank_weight)

    if not results:
        print(f"No results for '{args.query}'.")
    else:
        print(f"{len(results)} ranked result(s) for '{args.query}':\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title'] or '(no title)'}  [score={r['score']}, tfidf={r['tfidf']}, pagerank={r['pagerank']}]")
            print(f"   {r['url']}")