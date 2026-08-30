import { useState, useCallback } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";
const PAGE_SIZE = 10;

function highlightTerms(text, query) {
  if (!text) return text;
  const words = query.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return text;
  const pattern = new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "ig");
  const parts = text.split(pattern);
  return parts.map((part, i) =>
    words.some((w) => w.toLowerCase() === part.toLowerCase()) ? (
      <mark key={i}>{part}</mark>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [errorMessage, setErrorMessage] = useState("");

  const runSearch = useCallback(async (q, pageNum) => {
    if (!q.trim()) return;
    setStatus("loading");
    setErrorMessage("");
    try {
      const url = `${API_BASE}/search?q=${encodeURIComponent(q)}&page=${pageNum}&page_size=${PAGE_SIZE}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Server responded with ${res.status}`);
      const json = await res.json();
      setData(json);
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMessage(
        err instanceof TypeError
          ? "Can't reach the API. Is it running? (uvicorn api.main:app --reload)"
          : err.message
      );
    }
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmittedQuery(query);
    setPage(1);
    runSearch(query, 1);
  };

  const goToPage = (nextPage) => {
    setPage(nextPage);
    runSearch(submittedQuery, nextPage);
  };

  return (
    <div className="page">
      <header className="masthead">
        <div className="wordmark">
          <span className="dot" aria-hidden="true" />
          MINI SEARCH ENGINE
        </div>
        <p className="tagline">crawl &middot; index &middot; rank &middot; serve</p>
      </header>

      <form className="search-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the crawled index…"
          aria-label="Search query"
          autoFocus
        />
        <button type="submit" disabled={status === "loading" || !query.trim()}>
          Search
        </button>
      </form>

      <main className="results-area">
        {status === "idle" && (
          <p className="hint">Enter a query to search pages this crawler has indexed.</p>
        )}

        {status === "loading" && (
          <div className="loading" role="status">
            <span className="spinner" aria-hidden="true" />
            Searching…
          </div>
        )}

        {status === "error" && (
          <div className="error-panel" role="alert">
            <strong>Search failed.</strong>
            <p>{errorMessage}</p>
          </div>
        )}

        {status === "success" && data && data.results.length === 0 && (
          <div className="empty-panel">
            <p>No matches for &ldquo;{data.query}&rdquo;.</p>
            <p className="hint">Try a different term, or crawl more pages first.</p>
          </div>
        )}

        {status === "success" && data && data.results.length > 0 && (
          <>
            <p className="result-meta">
              {data.total_results} result{data.total_results !== 1 ? "s" : ""} for{" "}
              <strong>&ldquo;{data.query}&rdquo;</strong>
            </p>

            <ul className="result-list">
              {data.results.map((r) => (
                <li key={r.url} className="result-card">
                  <a
                    className="result-title"
                    href={r.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {highlightTerms(r.title || "(untitled page)", data.query)}
                  </a>
                  <div className="result-url">{r.url}</div>

                  <div className="signal-readout" aria-label="Ranking signal readout">
                    <span className="signal">
                      <span className="signal-label">score</span>
                      <span className="signal-value">{r.score.toFixed(4)}</span>
                    </span>
                    <span className="signal">
                      <span className="signal-label">tf-idf</span>
                      <span className="signal-value">{r.tfidf.toFixed(2)}</span>
                    </span>
                    <span className="signal">
                      <span className="signal-label">pagerank</span>
                      <span className="signal-value">{r.pagerank.toFixed(6)}</span>
                    </span>
                  </div>
                </li>
              ))}
            </ul>

            {data.total_pages > 1 && (
              <nav className="pagination" aria-label="Search results pages">
                <button
                  onClick={() => goToPage(page - 1)}
                  disabled={page <= 1 || status === "loading"}
                >
                  ← Prev
                </button>
                <span className="page-indicator">
                  page <strong>{data.page}</strong> / {data.total_pages}
                </span>
                <button
                  onClick={() => goToPage(page + 1)}
                  disabled={page >= data.total_pages || status === "loading"}
                >
                  Next →
                </button>
              </nav>
            )}
          </>
        )}
      </main>

      <footer className="footer">
        <span className="mono">Day 6 · Mini Search Engine · built from scratch</span>
      </footer>
    </div>
  );
}
