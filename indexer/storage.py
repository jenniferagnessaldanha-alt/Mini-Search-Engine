"""
Day 3 — Inverted index storage (PostgreSQL)

Table: inverted_index(term, doc_id, frequency)
  - One row per (term, document) pair that occurs in that document,
    with how many times the term appears (its term frequency, needed
    for Day 4's TF-IDF ranking).
  - An index on `term` makes "find all docs containing X" fast —
    exactly the lookup a search does.
"""

import os
from collections import Counter

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/mini_search_engine"


def get_connection():
    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    return psycopg2.connect(dsn)


def init_index_tables() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inverted_index (
                    term TEXT NOT NULL,
                    doc_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
                    frequency INTEGER NOT NULL,
                    PRIMARY KEY (term, doc_id)
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_inverted_index_term ON inverted_index(term);")
        conn.commit()


def fetch_all_pages():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, url, title, text FROM pages;")
            return cur.fetchall()


def clear_index() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE inverted_index;")
        conn.commit()


def index_document(doc_id: int, terms: list[str]) -> None:
    term_counts = Counter(terms)
    if not term_counts:
        return
    rows = [(term, doc_id, count) for term, count in term_counts.items()]
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO inverted_index (term, doc_id, frequency)
                VALUES %s
                ON CONFLICT (term, doc_id) DO UPDATE SET frequency = EXCLUDED.frequency;
                """,
                rows,
            )
        conn.commit()


def docs_containing(term: str) -> set[int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT doc_id FROM inverted_index WHERE term = %s;", (term,))
            return {row[0] for row in cur.fetchall()}


def get_pages_by_ids(doc_ids: list[int]):
    if not doc_ids:
        return []
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, url, title FROM pages WHERE id = ANY(%s);",
                (doc_ids,),
            )
            return cur.fetchall()


def index_size() -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT term) FROM inverted_index;")
            return cur.fetchone()[0]