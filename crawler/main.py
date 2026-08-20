"""
Day 1 — Mini Search Engine: Web Crawler (BFS)

Architecture
------------
- URL Frontier: a FIFO queue (collections.deque) holding (url, depth) pairs.
  This is what makes the traversal BFS: we fully explore depth N before
  moving to depth N+1.
- Visited Set: a set of normalized URLs already fetched, so we never
  crawl the same page twice.
- Politeness: each domain's robots.txt is fetched once and cached; we
  refuse to crawl any path disallowed for our user agent.
- Scope control: --depth caps how far from the seed we go, and
  --same-domain-only restricts the crawl to the seed's domain (common
  for a first working crawler, since the open web is unbounded).

Usage
-----
    python crawler/main.py --seed https://example.com --depth 2

Output
------
Each successfully crawled page is appended to `crawled_pages.jsonl`
as one JSON object per line: {url, title, text, depth, crawled_at}.
This file is what Day 2 will load into Postgres, and what Day 3 will
tokenize and index.
"""

import argparse
import json
import time
import urllib.robotparser
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

USER_AGENT = "MiniSearchBot/0.1 (+https://github.com/you/mini-search-engine)"
REQUEST_TIMEOUT = 8  # seconds
POLITENESS_DELAY = 1.0  # seconds between requests to the SAME domain


def normalize_url(url: str) -> str:
    """Strip fragments (#section) so the same page isn't queued twice."""
    url, _frag = urldefrag(url)
    if url.endswith("/") and url.count("/") > 3:
        url = url.rstrip("/")
    return url


class RobotsCache:
    """Fetches and caches robots.txt per domain so we only fetch it once."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _get_parser(self, domain: str, scheme: str) -> urllib.robotparser.RobotFileParser:
        if domain not in self._parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{scheme}://{domain}/robots.txt"
            try:
                resp = requests.get(robots_url, headers={"User-Agent": self.user_agent}, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    rp.parse([])  # no robots.txt -> treat as "allow all"
            except requests.RequestException:
                rp.parse([])
            self._parsers[domain] = rp
        return self._parsers[domain]

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        parser = self._get_parser(parsed.netloc, parsed.scheme)
        return parser.can_fetch(self.user_agent, url)


class Crawler:
    def __init__(self, seed_url: str, max_depth: int = 2, same_domain_only: bool = True, max_pages: int = 200):
        self.seed_url = normalize_url(seed_url)
        self.seed_domain = urlparse(self.seed_url).netloc
        self.max_depth = max_depth
        self.same_domain_only = same_domain_only
        self.max_pages = max_pages

        self.frontier: deque[tuple[str, int]] = deque([(self.seed_url, 0)])
        self.visited: set[str] = set()
        self.robots = RobotsCache(USER_AGENT)
        self._last_fetch_at_by_domain: dict[str, float] = {}

    def _respect_politeness(self, domain: str) -> None:
        last = self._last_fetch_at_by_domain.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < POLITENESS_DELAY:
                time.sleep(POLITENESS_DELAY - elapsed)
        self._last_fetch_at_by_domain[domain] = time.monotonic()

    def _in_scope(self, url: str) -> bool:
        if not self.same_domain_only:
            return True
        return urlparse(url).netloc == self.seed_domain

    def _extract_links(self, base_url: str, soup: BeautifulSoup) -> list[str]:
        links = []
        for a in soup.find_all("a", href=True):
            absolute = urljoin(base_url, a["href"])
            absolute = normalize_url(absolute)
            if absolute.startswith("http") and self._in_scope(absolute):
                links.append(absolute)
        return links

    def _fetch(self, url: str) -> requests.Response | None:
        try:
            return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            print(f"  [skip] fetch error for {url}: {e}")
            return None

    def crawl(self):
        pages_crawled = 0

        with open("crawled_pages.jsonl", "w", encoding="utf-8") as out:
            while self.frontier and pages_crawled < self.max_pages:
                url, depth = self.frontier.popleft()

                if url in self.visited:
                    continue
                if depth > self.max_depth:
                    continue
                if not self.robots.can_fetch(url):
                    print(f"  [skip] disallowed by robots.txt: {url}")
                    self.visited.add(url)
                    continue

                domain = urlparse(url).netloc
                self._respect_politeness(domain)

                print(f"[depth {depth}] crawling: {url}")
                response = self._fetch(url)
                self.visited.add(url)

                if response is None or response.status_code != 200:
                    continue
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                text = " ".join(soup.get_text(separator=" ").split())

                record = {
                    "url": url,
                    "title": title,
                    "text": text[:20000],  # cap to keep the file sane on large pages
                    "depth": depth,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                }
                out.write(json.dumps(record) + "\n")
                pages_crawled += 1

                if depth < self.max_depth:
                    for link in self._extract_links(url, soup):
                        if link not in self.visited:
                            self.frontier.append((link, depth + 1))

        print(f"\nDone. Crawled {pages_crawled} pages -> crawled_pages.jsonl")


def parse_args():
    p = argparse.ArgumentParser(description="Day 1: BFS web crawler")
    p.add_argument("--seed", required=True, help="Seed URL to start crawling from")
    p.add_argument("--depth", type=int, default=2, help="Max link depth from the seed")
    p.add_argument("--max-pages", type=int, default=200, help="Stop after crawling this many pages")
    p.add_argument("--allow-external", action="store_true", help="Follow links outside the seed domain")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    crawler = Crawler(
        seed_url=args.seed,
        max_depth=args.depth,
        same_domain_only=not args.allow_external,
        max_pages=args.max_pages,
    )
    crawler.crawl()
