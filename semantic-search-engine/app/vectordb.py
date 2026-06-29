"""
vectordb.py — ChromaDB wrapper for persistent vector storage.

Provides a clean interface for upserting code-chunk embeddings and
performing top-k semantic similarity searches.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# pyrefly: ignore [missing-import]
import chromadb
# pyrefly: ignore [missing-import]
from chromadb.config import Settings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_COLLECTION_NAME = "code_chunks"
DEFAULT_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_store")
DEFAULT_TOP_K = 5


# ---------------------------------------------------------------------------
# Data class for search results
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """A single search hit returned by the vector store."""

    text: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    score: float  # similarity score (higher = more similar)


# ---------------------------------------------------------------------------
# Vector DB wrapper
# ---------------------------------------------------------------------------

class VectorStore:
    """Persistent ChromaDB-backed vector store for code chunks.

    Parameters
    ----------
    persist_dir : str
        Directory where ChromaDB will persist data on disk.
    collection_name : str
        Name of the ChromaDB collection to use.
    """

    def __init__(
        self,
        persist_dir: str = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> None:
        self.persist_dir = os.path.abspath(persist_dir)
        self.collection_name = collection_name

        os.makedirs(self.persist_dir, exist_ok=True)

        print(f"[VectorStore] Initializing ChromaDB at '{self.persist_dir}' ...")
        self._client = chromadb.PersistentClient(path=self.persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(
            f"[VectorStore] Collection '{self.collection_name}' ready -- "
            f"{self._collection.count()} existing documents"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Insert or update documents in the collection.

        Parameters
        ----------
        ids : list[str]
            Unique identifiers for each document.
        documents : list[str]
            The raw text of each chunk.
        embeddings : list[list[float]]
            Pre-computed embedding vectors.
        metadatas : list[dict]
            Metadata dicts (file_path, start_line, end_line, language).
        """
        if not ids:
            return

        # ChromaDB supports batched upserts; we chunk to avoid oversized payloads
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            self._collection.upsert(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )

        print(f"[VectorStore] Upserted {len(ids)} documents")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = DEFAULT_TOP_K,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Find the top-k most similar documents to a query embedding.

        Parameters
        ----------
        query_embedding : list[float]
            The embedding vector for the search query.
        top_k : int
            Number of results to return (default 5).
        where : dict, optional
            Metadata filter for ChromaDB.

        Returns
        -------
        list[SearchResult]
            Ranked list of results (best match first).
        """
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, self._collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        results = self._collection.query(**query_kwargs)

        hits: List[SearchResult] = []
        if not results["documents"] or not results["documents"][0]:
            return hits

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB returns cosine *distance* (0 = identical).
            # Convert to a similarity score in [0, 1].
            similarity = round(1.0 - dist, 4)

            hits.append(
                SearchResult(
                    text=doc,
                    file_path=meta.get("file_path", "unknown"),
                    start_line=int(meta.get("start_line", 0)),
                    end_line=int(meta.get("end_line", 0)),
                    language=meta.get("language", "unknown"),
                    score=similarity,
                )
            )

        return hits

    def reset_collection(self) -> None:
        """Delete and recreate the collection (useful for re-ingestion)."""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[VectorStore] Collection '{self.collection_name}' has been reset")

    @property
    def count(self) -> int:
        """Number of documents currently stored."""
        return self._collection.count()
