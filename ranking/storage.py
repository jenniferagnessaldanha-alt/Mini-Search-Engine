import os
import psycopg2
from psycopg2.extras import RealDictCursor

DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/mini_search_engine"


def get_connection():
    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    return psycopg2.connect(dsn)


def get_pages_by_ids(doc_ids: list[int]):
    if not doc_ids:
        return []
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, url, title FROM pages WHERE id = ANY(%s);", (doc_ids,))
            return cur.fetchall()