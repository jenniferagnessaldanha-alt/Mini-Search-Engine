"""
Day 4 — Simplified PageRank

    PR(p) = (1 - d) / N  +  d * sum( PR(q) / OutDegree(q) for each q linking to p )

d = 0.85 damping factor (standard value from the original PageRank
paper). Only links between pages that were actually crawled count.
"""

from collections import defaultdict

from storage import get_connection

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