"""
Day 3 — Build the inverted index, and query it.

Usage
-----
    python indexer/main.py                        # build/rebuild the index
    python indexer/main.py --query "web crawler"   # AND search
    python indexer/main.py --query "web crawler" --mode or
"""

import argparse
from dotenv import load_dotenv 
load_dotenv()

from tokenizer import tokenize
from storage import (
    init_index_tables, fetch_all_pages, clear_index, index_document,
    docs_containing, get_pages_by_ids, index_size,
)


def build_index() -> None:
    init_index_tables()
    pages = fetch_all_pages()
    if not pages:
        print("No pages found in the 'pages' table — run the crawler first (Day 1/2).")
        return

    print(f"Indexing {len(pages)} pages...")
    clear_index()

    for page in pages:
        combined_text = f"{page['title'] or ''} {page['text'] or ''}"
        terms = tokenize(combined_text)
        index_document(page["id"], terms)

    print(f"Done. Index now has {index_size()} unique terms across {len(pages)} pages.")


def search(query: str, mode: str = "and") -> list[dict]:
    terms = tokenize(query)
    if not terms:
        return []

    doc_sets = [docs_containing(term) for term in terms]

    if mode == "and":
        result_ids = set.intersection(*doc_sets) if doc_sets else set()
    else:
        result_ids = set.union(*doc_sets) if doc_sets else set()

    return get_pages_by_ids(list(result_ids))


def parse_args():
    p = argparse.ArgumentParser(description="Day 3: build and query the inverted index")
    p.add_argument("--query", help="Search the existing index instead of rebuilding it")
    p.add_argument("--mode", choices=["and", "or"], default="and", help="Boolean mode for multi-word queries")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.query:
        results = search(args.query, args.mode)
        if not results:
            print(f"No results for '{args.query}' (mode={args.mode}).")
        else:
            print(f"{len(results)} result(s) for '{args.query}' (mode={args.mode}):\n")
            for r in results:
                print(f"  - {r['title'] or '(no title)'}\n    {r['url']}")
    else:
        build_index()
