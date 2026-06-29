#!/usr/bin/env python3
"""
search.py — CLI semantic search over an ingested codebase.

Accepts a natural-language query and returns the top-k most relevant
code snippets using cosine similarity against stored embeddings.

Usage
-----
    python scripts/search.py "database connection logic"
    python scripts/search.py "authentication middleware" --top-k 10
"""

import argparse
import os
import sys
import textwrap

# Ensure the project root is on sys.path so we can import `app.*`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.embedder import CodeEmbedder
from app.vectordb import VectorStore


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

SEPARATOR = "-" * 60

def print_header(query: str) -> None:
    print()
    print("=" * 60)
    print("  Semantic Code Search Engine")
    print("=" * 60)
    print(f"  Query: \"{query}\"")
    print("=" * 60)
    print()


def print_result(rank: int, result) -> None:
    """Pretty-print a single search result."""
    print(f"  Result {rank}:")
    print(f"  File     : {result.file_path}")
    print(f"  Lines    : {result.start_line}-{result.end_line}")
    print(f"  Language : {result.language}")
    print(f"  Score    : {result.score:.4f}")
    print(f"  Snippet  :")
    print()

    # Indent snippet for readability and truncate very long ones
    snippet_lines = result.text.rstrip("\n").split("\n")
    max_preview_lines = 20
    for line in snippet_lines[:max_preview_lines]:
        print(f"    {line}")
    if len(snippet_lines) > max_preview_lines:
        print(f"    ... ({len(snippet_lines) - max_preview_lines} more lines)")

    print()
    print(f"  {SEPARATOR}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Semantic search over an ingested codebase.",
    )
    parser.add_argument(
        "query",
        type=str,
        help='Natural-language query, e.g. "authentication logic"',
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "chroma_store"),
        help="ChromaDB persistence directory (default: ./chroma_store)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Search pipeline
# ---------------------------------------------------------------------------

def run_search(args: argparse.Namespace) -> None:
    """Execute the search pipeline."""

    # 1. Embed the query
    embedder = CodeEmbedder()
    query_embedding = embedder.embed_query(args.query)

    # 2. Retrieve results from the vector store
    store = VectorStore(persist_dir=args.persist_dir)

    if store.count == 0:
        print("\n[ERROR] The vector store is empty. Run ingestion first:")
        print("        python scripts/ingest.py\n")
        sys.exit(1)

    results = store.search(query_embedding, top_k=args.top_k)

    # 3. Display
    print_header(args.query)

    if not results:
        print("  No results found.\n")
        return

    for i, result in enumerate(results, start=1):
        print_result(i, result)

    print(f"  Showing top {len(results)} of {store.count} indexed chunks.\n")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    run_search(args)
