"""
config.py -- Centralized application configuration.

All settings are loaded from environment variables (prefixed ``SSE_``)
with sensible defaults.  A cached singleton is exposed via ``get_settings()``.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Every field can be overridden by setting ``SSE_<FIELD_NAME>`` in the
    environment or in a ``.env`` file at the project root.
    """

    # -- App metadata -------------------------------------------------------
    app_name: str = "Semantic Code Search Engine"
    app_version: str = "3.0.0"
    debug: bool = False

    # -- CORS ---------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://large-codebase-semantic-search-engi.vercel.app",
        "https://large-codebase-semantic-search-engine.vercel.app",
        "https://large-codebase-semantic-search-engine-frontend.vercel.app"
    ]

    # -- Embedding model ----------------------------------------------------
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 64

    # -- ChromaDB -----------------------------------------------------------
    chroma_persist_dir: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "chroma_store",
    )
    chroma_collection: str = "code_chunks"

    # -- Chunking -----------------------------------------------------------
    chunk_size: int = 400
    chunk_overlap: int = 50

    # -- Search defaults ----------------------------------------------------
    default_top_k: int = 5

    # -- Default data dir ---------------------------------------------------
    data_dir: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
    )

    # -- RAG / LLM ----------------------------------------------------------
    gemini_api_key: Optional[str] = None
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024
    rag_top_k: int = 10

    class Config:
        import os
        _project_root = os.path.dirname(os.path.dirname(__file__))
        env_prefix = "SSE_"
        env_file = os.path.join(_project_root, ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
