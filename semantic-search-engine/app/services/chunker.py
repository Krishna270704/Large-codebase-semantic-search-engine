"""
services/chunker.py -- Re-export of the Phase 1 chunking module.

Keeps all service-layer imports consistent at ``app.services.*``.
"""

from app.chunker import (  # noqa: F401
    IGNORED_DIRS,
    SUPPORTED_EXTENSIONS,
    CodeChunk,
    CodeChunker,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
)
