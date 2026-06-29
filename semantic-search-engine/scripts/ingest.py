#!/usr/bin/env python3
"""
ingest.py — Ingestion pipeline for the Semantic Code Search Engine.

Reads code files from a data directory, chunks them, generates embeddings,
and stores everything in ChromaDB for later semantic search.

Usage
-----
    python scripts/ingest.py                       # default: ./data
    python scripts/ingest.py --data-dir /path/to/code
    python scripts/ingest.py --reset               # wipe DB before ingesting
"""

import argparse
import os
import sys
import time

# Ensure the project root is on sys.path so we can import `app.*`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.chunker import CodeChunker
from app.embedder import CodeEmbedder
from app.vectordb import VectorStore


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest code files into the semantic search vector store.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "data"),
        help="Root directory of source code to ingest (default: ./data)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=400,
        help="Target tokens per chunk (default: 400)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=50,
        help="Overlap tokens between chunks (default: 50)",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default=os.path.join(PROJECT_ROOT, "chroma_store"),
        help="ChromaDB persistence directory (default: ./chroma_store)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the existing collection before ingesting",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_ingestion(args: argparse.Namespace) -> None:
    """Execute the full ingestion pipeline."""

    print("=" * 60)
    print("  Semantic Code Search Engine -- Ingestion Pipeline")
    print("=" * 60)
    print(f"  Data directory : {args.data_dir}")
    print(f"  Chunk size     : {args.chunk_size} tokens")
    print(f"  Chunk overlap  : {args.chunk_overlap} tokens")
    print(f"  Persist dir    : {args.persist_dir}")
    print("=" * 60)
    print()

    t_start = time.perf_counter()

    # ---- Step 1: Discover & chunk files --------------------------------
    print("[1/3] Chunking files ...")
    chunker = CodeChunker(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    chunks = chunker.chunk_directory(args.data_dir)
    if not chunks:
        print("[ERROR] No chunks produced -- check that your data directory contains supported files.")
        sys.exit(1)
    print(f"       -> {len(chunks)} chunks from {len(set(c.file_path for c in chunks))} files\n")

    # ---- Step 2: Generate embeddings -----------------------------------
    print("[2/3] Generating embeddings ...")
    embedder = CodeEmbedder()
    texts = [c.text for c in chunks]
    embeddings = embedder.embed_texts(texts)
    print(f"       -> {len(embeddings)} embeddings (dim={embedder.embedding_dimension})\n")

    # ---- Step 3: Store in ChromaDB -------------------------------------
    print("[3/3] Storing in ChromaDB ...")
    store = VectorStore(persist_dir=args.persist_dir)

    if args.reset:
        print("       [!] Resetting collection ...")
        store.reset_collection()

    ids = [c.chunk_id for c in chunks]
    metadatas = [
        {
            "file_path": c.file_path,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "language": c.language,
        }
        for c in chunks
    ]

    store.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    elapsed = time.perf_counter() - t_start
    print()
    print("=" * 60)
    print(f"  [OK] Ingestion complete -- {store.count} documents stored")
    print(f"  Time elapsed: {elapsed:.2f}s")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    run_ingestion(args)
