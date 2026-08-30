"""
Day 8 (polish pass) — Redis caching for search results.

We cache the RANKED result (before pagination), keyed on the
normalized query string, so repeated searches for the same query skip
recomputing PageRank + TF-IDF entirely. Pagination still happens fresh
on every request (cheap — just a list slice), so page 2 of a cached
query is still fast without needing a separate cache entry per page.

Deliberately fails soft: if Redis isn't running or unreachable, every
function here degrades to "no cache" (get returns None, set does
nothing) rather than raising and taking the whole API down. Caching is
a performance optimization, not a correctness requirement — losing it
should never break search.
"""

import json
import os

try:
    import redis
except ImportError:  # pragma: no cover - redis is in requirements.txt, but guard anyway
    redis = None

CACHE_TTL_SECONDS = 300  # 5 minutes
_client = None
_connection_attempted = False


def _get_client():
    global _client, _connection_attempted
    if _connection_attempted:
        return _client
    _connection_attempted = True

    if redis is None:
        return None

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        _client = client
    except Exception:
        _client = None  # Redis not reachable — silently disable caching
    return _client


def _cache_key(query: str) -> str:
    normalized = " ".join(query.lower().split())
    return f"search:{normalized}"


def get_cached_ranking(query: str):
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_cache_key(query))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_cached_ranking(query: str, ranked: list[dict]) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(_cache_key(query), CACHE_TTL_SECONDS, json.dumps(ranked))
    except Exception:
        pass  # caching is best-effort; a write failure shouldn't surface to the user


def cache_status() -> dict:
    client = _get_client()
    return {"connected": client is not None}


def flush_search_cache() -> None:
    """Called after a crawl completes, so freshly crawled content shows
    up immediately in search instead of waiting out the TTL on a
    previously-cached (now stale) ranking.
    """
    client = _get_client()
    if client is None:
        return
    try:
        for key in client.scan_iter("search:*"):
            client.delete(key)
    except Exception:
        pass  # best-effort; a failed flush just means results go stale until TTL expiry
