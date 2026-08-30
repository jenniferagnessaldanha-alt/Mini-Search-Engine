"""
Day 7 — End-to-end integration test.

Unlike the Day 1-5 unit tests (which test one piece in isolation, with
mocked/in-memory data), this test exercises the REAL pipeline against
a real database: crawl a real page -> tokenize + index it -> rank a
query against it -> confirm a search actually finds it.

We deliberately run the crawler and indexer as SUBPROCESSES (not
imports) — each of crawler/, indexer/, and ranking/ has its own
storage.py by design, so importing more than one of them in the same
process risks Python's module cache silently shadowing one "storage"
module with another. Subprocesses sidestep that entirely.

Run it
------
    python tests/test_integration.py
    docker compose exec api python tests/test_integration.py
"""

import os
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/mini_search_engine"


def _db_reachable() -> bool:
    try:
        import psycopg2
        dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
        conn = psycopg2.connect(dsn, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable] + cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_end_to_end_pipeline():
    if not _db_reachable():
        print(
            "SKIPPED: no Postgres connection available. Set DATABASE_URL or "
            "start the database — this is expected on a machine without it "
            "running, not a real failure."
        )
        return

    crawl_result = _run([
        "crawler/main.py",
        "--seed", "https://example.com",
        "--depth", "1",
        "--max-pages", "3",
    ])
    assert crawl_result.returncode == 0, f"Crawler failed:\n{crawl_result.stderr}"
    assert "crawled" in crawl_result.stdout.lower(), crawl_result.stdout

    index_result = _run(["indexer/main.py"])
    assert index_result.returncode == 0, f"Indexer failed:\n{index_result.stderr}"
    assert "Done" in index_result.stdout, index_result.stdout

    search_result = _run(["indexer/main.py", "--query", "example"])
    assert search_result.returncode == 0, f"Search failed:\n{search_result.stderr}"
    assert "example.com" in search_result.stdout.lower(), (
        f"Expected to find example.com in search results, got:\n{search_result.stdout}"
    )

    rank_result = _run(["ranking/main.py", "--query", "example"])
    assert rank_result.returncode == 0, f"Ranking failed:\n{rank_result.stderr}"
    assert "score=" in rank_result.stdout, rank_result.stdout

    print("End-to-end pipeline PASSED: crawl -> index -> search -> rank all connected correctly.")


if __name__ == "__main__":
    test_end_to_end_pipeline()