"""
embedder.py — Embedding logic using sentence-transformers.

Wraps the ``all-MiniLM-L6-v2`` model for converting text chunks
into dense vector embeddings suitable for semantic similarity search.
"""

import os
from typing import List, Optional

import numpy as np
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 64


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

class CodeEmbedder:
    """Generates dense vector embeddings for code chunks.

    Parameters
    ----------
    model_name : str
        Hugging Face model identifier (default ``all-MiniLM-L6-v2``).
    batch_size : int
        Number of texts to encode in a single forward pass (default 64).
    device : str | None
        Torch device string (``"cpu"``, ``"cuda"``, etc.).
        If *None*, sentence-transformers will auto-detect.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size

        print(f"[Embedder] Loading model '{model_name}' ...")
        self._model = SentenceTransformer(model_name, device=device)
        self._embedding_dim = self._model.get_embedding_dimension()
        print(f"[Embedder] Model loaded -- dimension={self._embedding_dim}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def embedding_dimension(self) -> int:
        """Dimensionality of the embedding vectors produced by the model."""
        return self._embedding_dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of text strings into embedding vectors.

        Parameters
        ----------
        texts : list[str]
            The texts to embed (code snippets, queries, etc.).

        Returns
        -------
        list[list[float]]
            One embedding vector per input text.
        """
        if not texts:
            return []

        embeddings = self._model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=len(texts) > self.batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,   # unit-norm → cosine ≡ dot product
        )

        # Convert numpy arrays → plain Python lists (required by ChromaDB)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query string.

        This is a convenience wrapper around :meth:`embed_texts` for a
        single input.
        """
        return self.embed_texts([query])[0]
