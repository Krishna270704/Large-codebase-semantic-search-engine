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
# Singleton holders  (populated lazily)
# ---------------------------------------------------------------------------

import threading
_lock = threading.RLock()

_embedder = None
_vector_store = None
_ingestion_service = None
_rag_service = None


def get_embedder():
    """Return the global ``CodeEmbedder`` singleton."""
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                from app.services.embedder import CodeEmbedder
                settings = get_settings()
                _embedder = CodeEmbedder(
                    model_name=settings.embedding_model,
                    batch_size=settings.embedding_batch_size,
                )
                logger.info("Embedder initialized lazily.")
    return _embedder


def get_vectordb():
    """Return the global ``VectorStore`` singleton."""
    global _vector_store
    if _vector_store is None:
        with _lock:
            if _vector_store is None:
                from app.services.vectordb import VectorStore
                settings = get_settings()
                _vector_store = VectorStore(
                    persist_dir=settings.chroma_persist_dir,
                    collection_name=settings.chroma_collection,
                )
                logger.info("VectorStore initialized lazily.")
    return _vector_store


# Alias for backward compatibility if any file calls get_vector_store
def get_vector_store():
    return get_vectordb()


def get_ingestion_service():
    """Return the global ``IngestionService`` singleton."""
    global _ingestion_service
    if _ingestion_service is None:
        with _lock:
            if _ingestion_service is None:
                from app.services.ingestion import IngestionService
                _ingestion_service = IngestionService(
                    embedder=get_embedder(),
                    store=get_vectordb(),
                )
                logger.info("IngestionService initialized lazily.")
    return _ingestion_service


def get_rag():
    """Return the global ``RAGService`` singleton."""
    global _rag_service
    if _rag_service is None:
        with _lock:
            if _rag_service is None:
                from app.services.rag import RAGService
                settings = get_settings()
                api_key = os.getenv("GEMINI_API_KEY") or settings.gemini_api_key
                if not api_key:
                    raise RuntimeError("Gemini API key not configured.")
                
                _rag_service = RAGService(
                    embedder=get_embedder(),
                    store=get_vectordb(),
                    top_k=settings.rag_top_k,
                )
                logger.info("RAGService initialized lazily.")
    return _rag_service


# Alias for backward compatibility if any file calls get_rag_service
def get_rag_service():
    return get_rag()


# ---------------------------------------------------------------------------
# Lifespan  (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager. Services are now loaded lazily, so we just log startup/shutdown."""
    settings = get_settings()
    logger.info("Starting %s v%s ... (lazy loading enabled)", settings.app_name, settings.app_version)

    yield  # ---- application serves requests here ----

    # Shutdown
    logger.info("Shutting down ...")
    global _embedder, _vector_store, _ingestion_service, _rag_service
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://large-codebase-semantic-search-engi.vercel.app",
        "https://large-codebase-semantic-search-engine.vercel.app",
        "https://large-codebase-semantic-search-engine-frontend.vercel.app",
    ],
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
