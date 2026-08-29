"""
Day 5 — Search API

Endpoints
---------
GET  /search?q=...&page=1&page_size=10   Ranked, paginated search results
POST /crawl                              Kick off a crawl (runs the crawler as a subprocess)
GET  /status                             Basic stats: pages indexed, terms, pending crawl queue

Run it
------
    uvicorn api.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive API docs.
"""

import os
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "indexer"))
from tokenizer import tokenize  # noqa: E402

from fastapi import FastAPI, Query
from pydantic import BaseModel

from .storage import get_pages_by_ids, page_count, pending_frontier_count, index_term_count
from .ranking_service import rank

app = FastAPI(title="Mini Search Engine API", version="0.1")


class CrawlRequest(BaseModel):
    seed: str
    depth: int = 2
    max_pages: int = 50
    strategy: str = "bfs"


@app.get("/")
def root():
    return {"message": "Mini Search Engine API. See /docs for usage."}


@app.get("/search")
def search(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    terms = tokenize(q)
    if not terms:
        return {"query": q, "total_results": 0, "page": page, "page_size": page_size, "results": []}

    ranked = rank(terms)
    total_results = len(ranked)

    start = (page - 1) * page_size
    end = start + page_size
    page_slice = ranked[start:end]

    doc_ids = [r["doc_id"] for r in page_slice]
    pages = {p["id"]: p for p in get_pages_by_ids(doc_ids)}

    results = []
    for r in page_slice:
        page_row = pages.get(r["doc_id"])
        if page_row:
            results.append({
                "url": page_row["url"],
                "title": page_row["title"],
                "score": r["score"],
                "tfidf": r["tfidf"],
                "pagerank": r["pagerank"],
            })

    return {
        "query": q,
        "total_results": total_results,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_results + page_size - 1) // page_size if total_results else 0,
        "results": results,
    }


@app.post("/crawl")
def crawl(req: CrawlRequest):
    project_root = os.path.join(os.path.dirname(__file__), "..")
    cmd = [
        sys.executable, "crawler/main.py",
        "--seed", req.seed,
        "--depth", str(req.depth),
        "--max-pages", str(req.max_pages),
        "--strategy", req.strategy,
    ]
    result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, timeout=300)
    return {
        "seed": req.seed,
        "returncode": result.returncode,
        "output": result.stdout[-2000:],
        "errors": result.stderr[-2000:] if result.returncode != 0 else None,
    }


@app.get("/status")
def status():
    return {
        "pages_crawled": page_count(),
        "unique_terms_indexed": index_term_count(),
        "pending_in_crawl_queue": pending_frontier_count(),
    }
