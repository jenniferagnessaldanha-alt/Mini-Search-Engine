"""
Tests the PageRank math directly (not through the DB), so they run
without a live Postgres connection.
"""

from collections import defaultdict

DAMPING = 0.85
ITERATIONS = 30


def run_pagerank(doc_ids: list[int], outgoing: dict[int, list[int]]) -> dict[int, float]:
    n = len(doc_ids)
    pr = {d: 1.0 / n for d in doc_ids}
    incoming = defaultdict(list)
    for f, targets in outgoing.items():
        for t in targets:
            incoming[t].append(f)
    out_degree = {d: len(outgoing.get(d, [])) for d in doc_ids}

    for _ in range(ITERATIONS):
        new_pr = {}
        dangling_sum = sum(pr[d] for d in doc_ids if out_degree[d] == 0)
        for d in doc_ids:
            incoming_score = sum(pr[q] / out_degree[q] for q in incoming.get(d, []) if out_degree[q] > 0)
            new_pr[d] = (1 - DAMPING) / n + DAMPING * (incoming_score + dangling_sum / n)
        pr = new_pr
    return pr


def test_scores_sum_to_approximately_one():
    pr = run_pagerank([1, 2, 3], {1: [2], 2: [3], 3: [1]})
    assert abs(sum(pr.values()) - 1.0) < 1e-6


def test_most_linked_page_wins():
    # Pages 2, 3, 4 all link to page 1 -> page 1 should rank highest.
    pr = run_pagerank([1, 2, 3, 4], {2: [1], 3: [1], 4: [1]})
    assert pr[1] == max(pr.values())


def test_symmetric_graph_gives_equal_rank():
    # A cycle: every page has exactly one inbound and one outbound link.
    pr = run_pagerank([1, 2, 3], {1: [2], 2: [3], 3: [1]})
    values = list(pr.values())
    assert max(values) - min(values) < 1e-6


def test_isolated_page_gets_baseline_rank():
    # Page 5 has no links in or out — should settle near the damping baseline.
    pr = run_pagerank([1, 2, 5], {1: [2], 2: [1]})
    baseline = (1 - DAMPING) / 3
    assert abs(pr[5] - baseline) < 0.05


if __name__ == "__main__":
    test_scores_sum_to_approximately_one()
    test_most_linked_page_wins()
    test_symmetric_graph_gives_equal_rank()
    test_isolated_page_gets_baseline_rank()
    print("All Day 4 PageRank tests passed.")
