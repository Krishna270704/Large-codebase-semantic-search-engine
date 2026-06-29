"""
services/vectordb.py -- Re-export of the Phase 1 vector-store module.
"""

from app.vectordb import (  # noqa: F401
    DEFAULT_COLLECTION_NAME,
    DEFAULT_PERSIST_DIR,
    DEFAULT_TOP_K,
    SearchResult,
    VectorStore,
)
