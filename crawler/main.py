"""
Day 1+2 — Mini Search Engine: Web Crawler

Day 1 gave us: BFS traversal, URL frontier, visited-set, robots.txt
respect, depth/domain limits.

Day 2 adds:
- DFS mode as an alternative to BFS (--strategy dfs), so you can
  compare traversal order/behavior.
- Hardened error handling: connection timeouts, too-many-redirects,
  non-HTML content, malformed HTML, HTTP error codes.
- Per-domain rate limiting (already had a basic delay; now backs off
  further on repeated failures for a domain).
- Persistent storage in PostgreSQL (crawler/storage.py) instead of a
  flat file. The frontier itself lives in the `frontier` table, so if
  the crawl is interrupted (Ctrl+C, crash, closed terminal), running
  the same command again picks up exactly where it left off instead
  of starting over.

Usage
-----
    python crawler/main.py --seed https://example.com --depth 2 --strategy bfs
    python crawler/main.py --seed https://example.com --depth 2 --strategy dfs
    python crawler/main.py --resume   # continue an interrupted crawl, no seed needed
"""

import argparse
import time
from urllib.parse import urljoin, urlparse, urldefrag
import urllib.robotparser

import requests
from bs4 import BeautifulSoup

from storage import (
    init_db, enqueue_url, pop_next_pending, mark_frontier_status,
    is_known, save_page, page_count, pending_count,
)

USER_AGENT = "MiniSearchBot/0.2 (+https://github.com/you/mini-search-engine)"
REQUEST_TIMEOUT = 8
BASE_POLITENESS_DELAY = 1.0
MAX_BACKOFF_DELAY = 30.0


def normalize_url(url: str) -> str:
    url, _frag = urldefrag(url)
    if url.endswith("/") and url.count("/") > 3:
        url = url.rstrip("/")
    return url


class RobotsCache:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._parsers = {}

    def _get_parser(self, domain: str, scheme: str):
        if domain not in self._parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{scheme}://{domain}/robots.txt"
            try:
                resp = requests.get(robots_url, headers={"User-Agent": self.user_agent}, timeout=REQUEST_TIMEOUT)
                rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            self._parsers[domain] = rp
        return self._parsers[domain]

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        return self._get_parser(parsed.netloc, parsed.scheme).can_fetch(self.user_agent, url)


class Crawler:
    def __init__(self, max_depth: int = 2, same_domain_only: bool = True,
                 max_pages: int = 200, strategy: str = "bfs"):
        self.max_depth = max_depth
        self.same_domain_only = same_domain_only
        self.max_pages = max_pages
        self.strategy = strategy  # "bfs" or "dfs"

        self.robots = RobotsCache(USER_AGENT)
        self._last_fetch_at_by_domain: dict[str, float] = {}
        self._consecutive_failures_by_domain: dict[str, int] = {}
        self.seed_domain: str | None = None

    def _in_scope(self, url: str) -> bool:
        if not self.same_domain_only or self.seed_domain is None:
            return True
        return urlparse(url).netloc == self.seed_domain

    def _politeness_delay(self, domain: str) -> None:
        failures = self._consecutive_failures_by_domain.get(domain, 0)
        delay = min(BASE_POLITENESS_DELAY * (2 ** failures), MAX_BACKOFF_DELAY)

        last = self._last_fetch_at_by_domain.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self._last_fetch_at_by_domain[domain] = time.monotonic()

    def _record_result(self, domain: str, success: bool) -> None:
        if success:
            self._consecutive_failures_by_domain[domain] = 0
        else:
            self._consecutive_failures_by_domain[domain] = self._consecutive_failures_by_domain.get(domain, 0) + 1

    def _extract_links(self, base_url: str, soup: BeautifulSoup) -> list[str]:
        links = []
        for a in soup.find_all("a", href=True):
            absolute = normalize_url(urljoin(base_url, a["href"]))
            if absolute.startswith("http") and self._in_scope(absolute):
                links.append(absolute)
        return list(reversed(links)) if self.strategy == "dfs" else links

    def _fetch(self, url: str):
        try:
            return requests.get(
                url, headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT, allow_redirects=True,
            )
        except requests.exceptions.Timeout:
            print(f"  [fail] timeout: {url}")
        except requests.exceptions.TooManyRedirects:
            print(f"  [fail] too many redirects: {url}")
        except requests.exceptions.ConnectionError:
            print(f"  [fail] connection error: {url}")
        except requests.RequestException as e:
            print(f"  [fail] request error for {url}: {e}")
        return None

    def seed(self, seed_url: str) -> None:
        seed_url = normalize_url(seed_url)
        self.seed_domain = urlparse(seed_url).netloc
        if not is_known(seed_url):
            enqueue_url(seed_url, 0)

    def crawl(self) -> None:
        crawled_this_run = 0

        while crawled_this_run < self.max_pages:
            row = pop_next_pending(self.strategy)
            if row is None:
                print("Frontier is empty — nothing left to crawl.")
                break

            frontier_id, url, depth = row["id"], row["url"], row["depth"]

            if depth > self.max_depth:
                mark_frontier_status(frontier_id, "done")
                continue
            if not self.robots.can_fetch(url):
                print(f"  [skip] disallowed by robots.txt: {url}")
                mark_frontier_status(frontier_id, "done")
                continue

            domain = urlparse(url).netloc
            self._politeness_delay(domain)

            print(f"[{self.strategy}, depth {depth}] crawling: {url}")
            response = self._fetch(url)

            if response is None:
                self._record_result(domain, success=False)
                mark_frontier_status(frontier_id, "failed")
                continue

            if response.status_code != 200:
                print(f"  [fail] HTTP {response.status_code}: {url}")
                self._record_result(domain, success=False)
                mark_frontier_status(frontier_id, "failed")
                continue

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                mark_frontier_status(frontier_id, "done")
                self._record_result(domain, success=True)
                continue

            try:
                soup = BeautifulSoup(response.text, "html.parser")
            except Exception as e:
                print(f"  [fail] malformed HTML at {url}: {e}")
                self._record_result(domain, success=False)
                mark_frontier_status(frontier_id, "failed")
                continue

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            text = " ".join(soup.get_text(separator=" ").split())[:20000]

            save_page(url, title, text, depth)
            mark_frontier_status(frontier_id, "done")
            self._record_result(domain, success=True)
            crawled_this_run += 1

            if depth < self.max_depth:
                for link in self._extract_links(url, soup):
                    if not is_known(link):
                        enqueue_url(link, depth + 1)

        print(f"\nThis run: crawled {crawled_this_run} pages.")
        print(f"Total pages in DB: {page_count()}. Still pending in frontier: {pending_count()}.")


def parse_args():
    p = argparse.ArgumentParser(description="Day 1+2: crawler with DFS/BFS, Postgres storage, resumability")
    p.add_argument("--seed", help="Seed URL (omit with --resume to continue prior crawl)")
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=200, help="Max pages to crawl in this run")
    p.add_argument("--allow-external", action="store_true")
    p.add_argument("--strategy", choices=["bfs", "dfs"], default="bfs")
    p.add_argument("--resume", action="store_true", help="Continue crawling from the existing frontier")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    init_db()

    crawler = Crawler(
        max_depth=args.depth,
        same_domain_only=not args.allow_external,
        max_pages=args.max_pages,
        strategy=args.strategy,
    )

    if not args.resume:
        if not args.seed:
            raise SystemExit("Provide --seed URL, or use --resume to continue a prior crawl.")
        crawler.seed(args.seed)

    crawler.crawl()