"""
embedder.py — Embedding logic using Google Gemini.

Wraps the ``text-embedding-004`` model for converting text chunks
into dense vector embeddings suitable for semantic similarity search.
"""

import os
from typing import List

from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL_NAME = "gemini-embedding-001"
DEFAULT_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

class CodeEmbedder:
    """Generates dense vector embeddings for code chunks.

    Parameters
    ----------
    model_name : str
        Gemini model identifier (default ``text-embedding-004``).
    batch_size : int
        Number of texts to encode in a single API call (default 100).
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._client = None
        self._embedding_dim = 768

    def get_client(self):
        """Create a singleton get_client() that loads the client only on first use."""
        if self._client is None:
            print(f"[Embedder] Loading Gemini model '{self.model_name}' ...")
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                from app.config import get_settings
                api_key = get_settings().gemini_api_key
            self._client = genai.Client(api_key=api_key)
            print(f"[Embedder] Model loaded -- dimension={self._embedding_dim}")
        return self._client

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

        client = self.get_client()
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            response = client.models.embed_content(
                model=self.model_name,
                contents=batch_texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=self._embedding_dim
                )
            )
            for e in response.embeddings:
                embeddings.append(e.values)

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query string."""
        return self.embed_texts([query])[0]
