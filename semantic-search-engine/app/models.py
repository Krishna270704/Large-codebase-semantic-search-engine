"""
models.py -- Pydantic v2 request / response schemas for the REST API.

All data contracts live here so routers stay thin and serialization
is consistent across endpoints.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    """Body for ``POST /api/v1/ingest``."""

    directory: Optional[str] = Field(
        default=None,
        description="Absolute or relative path to the directory to ingest.",
        examples=["./data", "C:/projects/my-app/src"],
    )
    github_url: Optional[str] = Field(
        default=None,
        description="URL of a GitHub repository to clone and ingest.",
        examples=["https://github.com/tiangolo/fastapi"],
    )
    reset: bool = Field(
        default=True,
        description="If true, wipe the existing collection before ingesting.",
    )
    chunk_size: Optional[int] = Field(
        default=None,
        ge=50,
        le=2000,
        description="Override: target tokens per chunk.",
    )
    chunk_overlap: Optional[int] = Field(
        default=None,
        ge=0,
        le=500,
        description="Override: overlap tokens between chunks.",
    )


class IngestResponse(BaseModel):
    """Response for ``POST /api/v1/ingest``."""
    
    success: bool = True
    message: str = "Repository ingestion started."

class IngestStatusResponse(BaseModel):
    """Response for ``GET /api/v1/ingest/status``."""
    status: str
    files_processed: int = 0
    total_files: int = 0
    percentage: int = 0


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchResultItem(BaseModel):
    """A single search hit."""

    file_path: str
    start_line: int
    end_line: int
    language: str
    score: float = Field(..., description="Cosine similarity (0-1, higher is better).")
    snippet: str


class SearchResponse(BaseModel):
    """Response for ``GET /api/v1/search``."""

    query: str
    total_indexed: int
    results: List[SearchResultItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Ask (RAG)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(
        ...,
        description="Message role: 'user' or 'assistant'.",
        examples=["user", "assistant"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Message content.",
    )


class AskRequest(BaseModel):
    """Body for ``POST /api/v1/ask``.

    Supports conversation history for multi-turn RAG.
    The ``stream`` flag controls whether the response is sent as
    Server-Sent Events (streaming) or as a single JSON payload.
    """

    question: str = Field(
        ...,
        min_length=1,
        description="Natural-language question about the codebase.",
        examples=["How does the authentication system work?"],
    )
    history: List[ChatMessage] = Field(
        default_factory=list,
        description=(
            "Previous conversation turns (last 3-6 messages recommended). "
            "Each entry must have 'role' and 'content' fields."
        ),
    )
    stream: bool = Field(
        default=True,
        description="If true, stream the response as Server-Sent Events.",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Override: number of code chunks to retrieve (default from config).",
    )


class AskSourceItem(BaseModel):
    """A source citation in a RAG answer."""

    file_path: str
    relative_path: str = ""
    start_line: int
    end_line: int
    language: str
    score: float
    snippet: str
    reason: str = ""
    repository_name: str = ""


class AskResponse(BaseModel):
    """Response for ``POST /api/v1/ask`` (non-streaming mode)."""

    question: str
    answer: str
    sources: List[AskSourceItem] = Field(default_factory=list)
    model: str = ""
    tokens_used: int = 0


class ExplainRequest(BaseModel):
    """Body for ``POST /api/v1/explain``."""
    file_path: str
    snippet: str
    stream: bool = True


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Response for ``GET /health`` and ``GET /api/v1/health``."""

    status: str = "ok"
    llm: str = "connected"
    vectordb: str = "connected"

