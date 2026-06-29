"""
main.py -- FastAPI application entry point.

Initializes the app, loads heavy resources (embedding model, vector store,
RAG service) **once** at startup via the lifespan context manager, registers
routers, and configures CORS middleware.

Run with::

    uvicorn app.main:app --reload
"""
import os
from dotenv import load_dotenv

_project_root = os.path.dirname(os.path.dirname(__file__))
_env_path = os.path.join(_project_root, ".env")
load_dotenv(_env_path)

print("API KEY:", os.getenv("GEMINI_API_KEY"))

import logging
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.models import HealthResponse
from app.routers import ask, ingest, search

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton holders  (populated during lifespan startup)
# ---------------------------------------------------------------------------

_embedder = None
_vector_store = None
_ingestion_service = None
_rag_service = None


def get_embedder():
    """Return the global ``CodeEmbedder`` singleton.

    Raises ``RuntimeError`` if called before startup completes.
    """
    if _embedder is None:
        raise RuntimeError("Embedder has not been initialized yet.")
    return _embedder


def get_vector_store():
    """Return the global ``VectorStore`` singleton."""
    if _vector_store is None:
        raise RuntimeError("VectorStore has not been initialized yet.")
    return _vector_store


def get_ingestion_service():
    """Return the global ``IngestionService`` singleton."""
    if _ingestion_service is None:
        raise RuntimeError("IngestionService has not been initialized yet.")
    return _ingestion_service


def get_rag_service():
    """Return the global ``RAGService`` singleton.

    Raises ``RuntimeError`` if the RAG service was not initialized
    (typically because ``GEMINI_API_KEY`` is not set).
    """
    if _rag_service is None:
        raise RuntimeError(
            "RAGService has not been initialized. "
            "Set GEMINI_API_KEY in your environment or .env file."
        )
    return _rag_service


# ---------------------------------------------------------------------------
# Lifespan  (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load expensive resources once at startup; release on shutdown."""
    global _embedder, _vector_store, _ingestion_service, _rag_service

    settings = get_settings()
    logger.info("Starting %s v%s ...", settings.app_name, settings.app_version)

    # 1. Load embedding model  (~3-5 s on first run when downloading)
    from app.services.embedder import CodeEmbedder

    _embedder = CodeEmbedder(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
    )
    logger.info(
        "Embedder ready  (model=%s, dim=%d)",
        settings.embedding_model,
        _embedder.embedding_dimension,
    )

    # 2. Initialize persistent vector store
    from app.services.vectordb import VectorStore

    _vector_store = VectorStore(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
    )
    logger.info(
        "VectorStore ready  (%d documents in '%s')",
        _vector_store.count,
        settings.chroma_collection,
    )

    # 3. Create ingestion service  (shares embedder + store singletons)
    from app.services.ingestion import IngestionService

    _ingestion_service = IngestionService(
        embedder=_embedder,
        store=_vector_store,
    )
    logger.info("IngestionService ready")

    # 4. Create RAG service  (requires an LLM API key)
    api_key = os.getenv("GEMINI_API_KEY") or settings.gemini_api_key
    logger.info("DEBUG API KEY is: '%s'", api_key)

    if not api_key:
        raise ValueError("Gemini API key not configured.")

    from app.services.rag import RAGService

    _rag_service = RAGService(
        embedder=_embedder,
        store=_vector_store,
        top_k=settings.rag_top_k,
    )
    logger.info("RAGService ready")

    logger.info("=== Startup complete -- all services initialized ===")

    yield  # ---- application serves requests here ----

    # Shutdown
    logger.info("Shutting down ...")
    _embedder = None
    _vector_store = None
    _ingestion_service = None
    _rag_service = None


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A semantic code search API that indexes local codebases and answers "
        "natural-language queries with the most relevant code snippets, "
        "powered by sentence-transformers, ChromaDB, and LLM-based RAG."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# -- CORS -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers ----------------------------------------------------------------

app.include_router(ingest.router)
app.include_router(search.router)
app.include_router(ask.router)


# ---------------------------------------------------------------------------
# Root / health
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Returns service health status.",
)
@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check API v1",
)
async def health_check() -> HealthResponse:
    """Return service health and basic statistics."""
    llm_status = "connected"
    system_status = "ok"
    
    if _rag_service is None:
        llm_status = "unavailable"
        system_status = "degraded"
        
    return HealthResponse(
        status=system_status,
        llm=llm_status,
        vectordb="connected",
    )


@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return {
        "message": f"{settings.app_name} v{settings.app_version}",
        "docs": "/docs",
        "health": "/health",
    }
