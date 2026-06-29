"""
routers/search.py -- Semantic search API endpoint.

GET /api/v1/search?q=<query>&k=<top_k>
    Converts a natural-language query into an embedding, performs cosine
    similarity search against ChromaDB, and returns ranked results.
"""

import logging

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Query, status

from app.models import SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over indexed code",
    description=(
        "Accepts a natural-language query and returns the top-k most "
        "semantically similar code snippets from the indexed codebase."
    ),
)
async def semantic_search(
    q: str = Query(
        ...,
        min_length=1,
        description="Natural-language search query.",
        examples=["database connection", "authentication logic"],
    ),
    k: int = Query(
        default=5,
        ge=1,
        le=50,
        description="Number of results to return (1-50, default 5).",
    ),
) -> SearchResponse:
    """Execute a semantic search and return ranked results."""
    from app.main import get_embedder, get_vector_store

    embedder = get_embedder()
    store = get_vector_store()

    if store.count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "The vector store is empty. "
                "Run ingestion first via POST /api/v1/ingest."
            ),
        )

    try:
        query_embedding = embedder.embed_query(q)
        hits = store.search(query_embedding, top_k=k)
    except Exception as exc:
        logger.exception("Search failed")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        )

    results = [
        SearchResultItem(
            file_path=hit.file_path,
            start_line=hit.start_line,
            end_line=hit.end_line,
            language=hit.language,
            score=hit.score,
            snippet=hit.text,
        )
        for hit in hits
    ]

    return SearchResponse(
        query=q,
        total_indexed=store.count,
        results=results,
    )
