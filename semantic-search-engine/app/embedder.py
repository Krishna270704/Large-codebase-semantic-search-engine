"""
embedder.py — Embedding logic using Google Gemini.

Wraps the ``text-embedding-004`` model for converting text chunks
into dense vector embeddings suitable for semantic similarity search.
"""

import os
import time
from collections import deque
from typing import List

from google import genai
from google.genai import types
from google.genai.errors import ClientError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL_NAME = "gemini-embedding-001"
DEFAULT_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()

    def wait(self):
        now = time.time()
        # Remove calls older than the period
        while self.calls and now - self.calls[0] > self.period:
            self.calls.popleft()
        
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
            # Remove again after sleeping
            now = time.time()
            while self.calls and now - self.calls[0] > self.period:
                self.calls.popleft()
        
        self.calls.append(time.time())

# Global rate limiter (90 calls per minute)
_rate_limiter = RateLimiter(max_calls=90, period=60.0)


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

class CodeEmbedder:
    """Generates dense vector embeddings for code chunks.

    Parameters
    ----------
    model_name : str
        Gemini model identifier (default ``gemini-embedding-001``).
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

    def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        """Encode a list of text strings into embedding vectors.

        Parameters
        ----------
        texts : list[str]
            The texts to embed (code snippets, queries, etc.).
        task_type : str
            The Gemini task type. Usually RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY.

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
            
            for attempt in range(1, 6):
                _rate_limiter.wait()
                try:
                    response = client.models.embed_content(
                        model=self.model_name,
                        contents=batch_texts,
                        config=types.EmbedContentConfig(
                            output_dimensionality=self._embedding_dim,
                            task_type=task_type
                        )
                    )
                    for e in response.embeddings:
                        embeddings.append(e.values)
                    break
                except ClientError as e:
                    if hasattr(e, "code") and e.code == 429 or "429" in str(e):
                        if attempt == 5:
                            raise
                        print(f"[Embedder] 429 Rate limit hit, retrying attempt {attempt}/5 with exponential backoff...")
                        time.sleep(2 ** attempt)
                    else:
                        raise

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query string."""
        return self.embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
