import os
import psycopg2
from psycopg2.extras import RealDictCursor

DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/mini_search_engine"


def get_connection():
    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    return psycopg2.connect(dsn)

def init_db() -> None:
    """Create all tables the API touches, if they don't already exist.
    Mirrors crawler/storage.py + indexer/storage.py's table definitions
    so the API works standalone (e.g. right after `docker compose up`,
    before anyone has run the crawler or indexer yet).
    """
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
                    status TEXT NOT NULL DEFAULT 'pending',
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inverted_index (
                    term TEXT NOT NULL,
                    doc_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
                    frequency INTEGER NOT NULL,
                    PRIMARY KEY (term, doc_id)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier(status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_inverted_index_term ON inverted_index(term);")
        conn.commit()


def get_pages_by_ids(doc_ids: list[int]):
    if not doc_ids:
        return []
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, url, title FROM pages WHERE id = ANY(%s);", (doc_ids,))
            return cur.fetchall()


def page_count() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pages;")
            return cur.fetchone()[0]


def pending_frontier_count() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM frontier WHERE status = 'pending';")
            return cur.fetchone()[0]


def index_term_count() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT term) FROM inverted_index;")
            return cur.fetchone()[0]