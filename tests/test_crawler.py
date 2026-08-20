import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawler.main import normalize_url, Crawler


def test_normalize_url_strips_fragment():
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"


def test_normalize_url_strips_trailing_slash():
    assert normalize_url("https://example.com/page/") == "https://example.com/page"


def test_normalize_url_keeps_root_slash():
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_crawler_same_domain_scope():
    c = Crawler(seed_url="https://example.com", max_depth=1)
    assert c._in_scope("https://example.com/other-page") is True
    assert c._in_scope("https://other-site.com/page") is False


def test_crawler_allows_external_when_flagged():
    c = Crawler(seed_url="https://example.com", max_depth=1, same_domain_only=False)
    assert c._in_scope("https://other-site.com/page") is True


if __name__ == "__main__":
    test_normalize_url_strips_fragment()
    test_normalize_url_strips_trailing_slash()
    test_normalize_url_keeps_root_slash()
    test_crawler_same_domain_scope()
    test_crawler_allows_external_when_flagged()
    print("All Day 1 tests passed.")
