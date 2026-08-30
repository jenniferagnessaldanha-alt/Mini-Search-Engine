# Mini Search Engine — Frontend

A single-page React UI for the search API built on Days 1–5. Enter a
query, see ranked results with the TF-IDF and PageRank signals that
produced the ranking, and page through results.

## Design notes

Dark "terminal-meets-searchlight" theme: Space Grotesk for headings,
Inter for body copy, JetBrains Mono for anything technical (URLs,
scores). The signature element is the **signal readout** on each
result card — since this whole project is about *how* ranking works,
the UI shows the score, tf-idf, and pagerank numbers openly instead of
hiding them behind a plain result list.

## Run it

Make sure the API (Day 5) is running first, in a separate terminal:

```bash
uvicorn api.main:app --reload
```

Then, in this `frontend` folder:

```bash
npm install
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`).

## Build for production

```bash
npm run build
```

Outputs to `dist/`.
