# 🔍 Mini Search Engine

A from-scratch search engine demonstrating web crawling, indexing, ranking algorithms, and search infrastructure — the core building blocks behind Google/Bing-scale systems.

```
Web Crawler → Indexer → Ranking Engine → Search API → UI
```

## Tech Stack

| Layer     | Tech                        |
|-----------|------------------------------|
| Backend   | Python (FastAPI)             |
| Storage   | PostgreSQL / Elasticsearch   |
| Cache     | Redis                        |
| Frontend  | React (Vite)                 |
| Deploy    | Docker / docker-compose      |

## Core Features

- [ ] Web crawler with BFS/DFS traversal
- [ ] Inverted index for fast lookups
- [ ] TF-IDF and PageRank ranking
- [ ] Query optimization & Redis caching
- [ ] Search UI with pagination

## 7-Day Build Roadmap

### Day 1 — Project Setup + Crawler Foundations ✅
- [x] Repo structure, virtualenv, `requirements.txt`
- [x] Crawler architecture: URL frontier, visited-set, robots.txt respect
- [x] Basic BFS crawler (fetch → extract links → enqueue)
- [x] Depth limit + domain restriction
- **Deliverable:** crawler traverses 50–100 pages from a seed URL
- **Status:** Done. `crawler/main.py` implements a BFS crawler with a
  `deque`-based frontier, a per-domain robots.txt cache, politeness
  delay, and same-domain scoping. Output is written to
  `crawled_pages.jsonl` (url, title, text, depth, timestamp) — ready
  for Day 2 to load into Postgres. Tests in `tests/test_crawler.py`.

### Day 2 — Crawler Hardening + Storage
- DFS mode option, compare crawl patterns
- Error handling: timeouts, redirects, duplicates, malformed HTML
- Rate limiting / politeness delay per domain
- Persist crawled pages (HTML + metadata) to PostgreSQL
- **Deliverable:** resumable crawler with structured storage

### Day 3 — Inverted Index
- Tokenization: lowercase, stopword removal, stemming
- Build inverted index (term → doc_id, positions/frequency)
- Store index in Elasticsearch (or custom structure)
- Boolean query support (AND/OR)
- **Deliverable:** millisecond-speed term lookups

### Day 4 — Ranking Engine
- TF-IDF relevance scoring
- Simplified PageRank from crawl link graph
- Combined weighted ranking score
- Benchmark against a hand-labeled query set
- **Deliverable:** `rank(query) → sorted doc_ids with scores`

### Day 5 — Search API + Caching
- FastAPI endpoints: `/search`, `/crawl`, `/status`
- Pagination (offset/limit)
- Redis caching for repeated queries
- Query optimization: spell-check, expansion (stretch goal)
- **Deliverable:** working REST API, ranked + paginated JSON

### Day 6 — Frontend UI
- React app: search bar + results list
- Wire up to FastAPI backend, loading/error states
- Pagination controls, highlighted query terms in snippets
- Responsive styling
- **Deliverable:** functioning search UI

### Day 7 — Integration, Testing & Deployment
- End-to-end test: crawl → index → rank → search → display
- Unit tests for indexer + ranking logic
- Dockerfile + docker-compose (API + Elasticsearch + Redis + Postgres)
- Architecture diagram + screenshots in README
- **Deliverable:** tagged `v1.0` release, pushed to GitHub

## Project Structure

```
mini-search-engine/
├── crawler/      # BFS/DFS web crawler
├── indexer/      # Tokenization + inverted index
├── ranking/      # TF-IDF + PageRank
├── api/          # FastAPI search endpoints
├── frontend/     # React UI
├── tests/        # Unit + integration tests
├── docs/         # Architecture notes, diagrams
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# start dependencies
docker-compose up -d   # postgres, redis, elasticsearch

# run crawler
python crawler/main.py --seed https://example.com --depth 2

# run API
uvicorn api.main:app --reload
```

## License

MIT
