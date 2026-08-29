"""
Day 2 — Storage layer (PostgreSQL)

Two tables:
- pages: one row per successfully crawled page (url, title, text, depth, crawled_at)
- frontier: the crawl queue itself, persisted so a crawl can be resumed
  after being interrupted (status: 'pending' | 'done' | 'failed')

Set the connection string via the DATABASE_URL environment variable, e.g.:
    postgresql://postgres:YOUR_PASSWORD@localhost:5432/mini_search_engine

If DATABASE_URL isn't set, we fall back to that same default so this
works out of the box after `CREATE DATABASE mini_search_engine;`.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/mini_search_engine"


def get_connection():
    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    return psycopg2.connect(dsn)


def init_db():
    """Create tables if they don't already exist. Safe to run every time."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    text TEXT,
                    depth INTEGER NOT NULL,
                    crawled_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS frontier (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    depth INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',  -- pending | done | failed
                    added_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS links (
                    id SERIAL PRIMARY KEY,
                    from_doc_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
                    to_url TEXT NOT NULL,
                    UNIQUE (from_doc_id, to_url)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier(status);")
        conn.commit()


def enqueue_url(url: str, depth: int) -> None:
    """Add a URL to the frontier if it isn't already known (visited or queued)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO frontier (url, depth, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT (url) DO NOTHING;
                """,
                (url, depth),
            )
        conn.commit()


def pop_next_pending(strategy: str = "bfs"):
    """Fetch the next pending URL. BFS takes the oldest-queued (FIFO, ORDER BY id ASC).
    DFS takes the most-recently-queued (LIFO, ORDER BY id DESC), which dives into
    each page's links before returning to siblings. Marking as done/failed happens
    separately after the crawl attempt.
    """
    order = "ASC" if strategy == "bfs" else "DESC"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, url, depth FROM frontier
                WHERE status = 'pending'
                ORDER BY id {order}
                LIMIT 1;
                """
            )
            row = cur.fetchone()
        conn.commit()
    return row


def mark_frontier_status(frontier_id: int, status: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE frontier SET status = %s WHERE id = %s;", (status, frontier_id))
        conn.commit()


def is_known(url: str) -> bool:
    """True if this URL has already been queued or crawled (dedup check)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM frontier WHERE url = %s;", (url,))
            return cur.fetchone() is not None


def save_page(url: str, title: str, text: str, depth: int) -> int:
    """Insert or update a page, returning its id (needed to store outgoing links)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pages (url, title, text, depth)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    title = EXCLUDED.title,
                    text = EXCLUDED.text,
                    crawled_at = now()
                RETURNING id;
                """,
                (url, title, text, depth),
            )
            page_id = cur.fetchone()[0]
        conn.commit()
    return page_id


def save_links(from_doc_id: int, to_urls: list[str]) -> None:
    """Record the outgoing links found on a page — this is the link graph
    that Day 4's PageRank walks over. We store target URLs as text (not
    doc_id) because the target may not have been crawled yet; ranking
    resolves URL -> doc_id at computation time, only counting links
    between pages that were actually crawled.
    """
    if not to_urls:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            from psycopg2.extras import execute_values
            execute_values(
                cur,
                """
                INSERT INTO links (from_doc_id, to_url)
                VALUES %s
                ON CONFLICT DO NOTHING;
                """,
                [(from_doc_id, url) for url in to_urls],
            )
        conn.commit()


def page_count() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pages;")
            return cur.fetchone()[0]


def pending_count() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM frontier WHERE status = 'pending';")
            return cur.fetchone()[0]