import sys
import os

# Add the crawler/ folder itself (not its parent) to sys.path, so
# `import storage` inside crawler/main.py resolves correctly — matching
# how main.py is actually run in practice (`python crawler/main.py`,
# from inside that folder's context).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "crawler"))

from main import normalize_url, Crawler  # noqa: E402


def test_normalize_url_strips_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_url_strips_trailing_slash():
    assert normalize_url("https://example.com/page/") == "https://example.com/page"


def test_normalize_url_keeps_root_slash():
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_crawler_same_domain_scope():
    # Day 2 changed Crawler's constructor to not take seed_url directly —
    # seeding is now a separate .seed() call, since the frontier lives in
    # Postgres and a fresh Crawler object doesn't own a single seed URL
    # the way the Day 1 version did.
    c = Crawler(max_depth=1)
    c.seed_domain = "example.com"
    assert c._in_scope("https://example.com/other-page") is True
    assert c._in_scope("https://other-site.com/page") is False


def test_crawler_allows_external_when_flagged():
    c = Crawler(max_depth=1, same_domain_only=False)
    c.seed_domain = "example.com"
    assert c._in_scope("https://other-site.com/page") is True


if __name__ == "__main__":
    test_normalize_url_strips_fragment()
    test_normalize_url_strips_trailing_slash()
    test_normalize_url_keeps_root_slash()
    test_crawler_same_domain_scope()
    test_crawler_allows_external_when_flagged()
    print("All Day 1/2 crawler tests passed.")