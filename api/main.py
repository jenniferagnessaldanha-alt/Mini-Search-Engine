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

Then open http://127.0.0.1:8000/docs for interactive API docs (FastAPI
generates this automatically — a good way to try endpoints in the browser).
"""

import os
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "indexer"))
from tokenizer import tokenize  # noqa: E402

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .storage import get_pages_by_ids, page_count, pending_frontier_count, index_term_count, init_db
from .ranking_service import rank
from .snippets import make_snippet
from . import cache

app = FastAPI(title="Mini Search Engine API", version="0.1")

# Allow the Vite dev server (frontend, Day 6) to call this API from the
# browser. Without this, the browser blocks the request before it even
# reaches FastAPI — the frontend sees it as "can't reach the API" even
# though the server is running fine, since this is a browser-side
# security restriction (CORS), not a networking failure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Ensure tables exist the moment the API starts — important for
    Docker Compose, where the API may start against a completely fresh,
    empty database before anyone has run the crawler yet.
    """
    init_db()


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

    # Check the cache first — a repeated query skips PageRank/TF-IDF
    # recomputation entirely. Cache stores the full ranked list (all
    # matches, unpaginated); pagination below always runs fresh since
    # slicing a list is essentially free.
    ranked = cache.get_cached_ranking(q)
    cache_hit = ranked is not None
    if not cache_hit:
        ranked = rank(terms)