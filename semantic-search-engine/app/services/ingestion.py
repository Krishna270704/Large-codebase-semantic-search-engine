"""
services/ingestion.py -- Ingestion orchestration service.

Coordinates the full pipeline:
    file discovery -> chunking -> embedding -> ChromaDB storage

Used by both the ``POST /api/v1/ingest`` endpoint and the CLI script.
"""

import logging
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional

from app.services.chunker import CodeChunker
from app.services.embedder import CodeEmbedder
from app.services.vectordb import VectorStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Outcome of a single ingestion run."""

    chunks_indexed: int
    files_processed: int
    elapsed_seconds: float
    total_stored: int
    files: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class IngestionService:
    """Orchestrates the full ingestion pipeline.

    Designed to be instantiated **once** at app startup and reused across
    requests.  The expensive ``CodeEmbedder`` and ``VectorStore`` singletons
    are injected so they can be shared with the search endpoint.

    Parameters
    ----------
    embedder : CodeEmbedder
        Pre-loaded embedding model (shared singleton).
    store : VectorStore
        Pre-initialized vector store (shared singleton).
    """

    def __init__(self, embedder: CodeEmbedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store
        self.state = {
            "status": "idle",
            "files_processed": 0,
            "total_files": 0,
            "percentage": 0
        }

    def get_status(self) -> dict:
        return self.state

    def ingest_directory(
        self,
        directory: str,
        *,
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        reset: bool = False,
        github_url: Optional[str] = None,
    ) -> IngestionResult:
        """Run the full ingestion pipeline on *directory*.

        Parameters
        ----------
        directory : str
            Root path to scan for source files.
        chunk_size : int
            Target tokens per chunk.
        chunk_overlap : int
            Overlap tokens between adjacent chunks.
        reset : bool
            If ``True``, wipe the collection before storing.

        Returns
        -------
        IngestionResult

        Raises
        ------
        FileNotFoundError
            If *directory* does not exist.
        ValueError
            If *chunk_overlap* >= *chunk_size*.
        """
        t0 = time.perf_counter()
        self.state = {
            "status": "running",
            "files_processed": 0,
            "total_files": 0,
            "percentage": 0
        }

        # 1. Chunk -----------------------------------------------------------
        logger.info("Chunking files in '%s' ...", directory)
        chunker = CodeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        try:
            files = chunker.discover_files(directory)
            total_files = len(files)
            self.state["total_files"] = total_files
            
            if total_files == 0:
                self.state["status"] = "completed"
                self.state["percentage"] = 100
                return IngestionResult(0, 0, 0.0, self._store.count, [])

            chunks = []
            files_processed = 0
            for fp in files:
                chunks.extend(chunker.chunk_file(fp))
                files_processed += 1
                self.state["files_processed"] = files_processed
                # The first 50% of progress is chunking files
                self.state["percentage"] = int((files_processed / total_files) * 50)

            # Calculate relative display paths
            def get_display_path(abs_path: str) -> str:
                try:
                    if f"data{os.sep}github{os.sep}" in directory:
                        parent = os.path.dirname(directory)
                        return os.path.relpath(abs_path, parent).replace(os.sep, "/")
                    return os.path.relpath(abs_path, directory).replace(os.sep, "/")
                except ValueError:
                    return abs_path

            files_list = list({get_display_path(c.file_path) for c in chunks})
            logger.info("Produced %d chunks from %d files", len(chunks), files_processed)

            if not chunks:
                self.state["status"] = "completed"
                self.state["percentage"] = 100
                return IngestionResult(0, 0, round(time.perf_counter() - t0, 2), self._store.count, [])

            # 2. Embed -----------------------------------------------------------
            logger.info("[Ingest] Generating embeddings started ...")
            texts = [c.text for c in chunks]
            
            # Since embedding can be slow, we'll embed in batches to update progress
            embeddings = []
            batch_size = 64
            total_chunks = len(texts)
            
            for i in range(0, total_chunks, batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_embeddings = self._embedder.embed_texts(batch_texts)
                embeddings.extend(batch_embeddings)
                
                # The next 40% of progress is embedding
                chunks_processed = min(i + batch_size, total_chunks)
                self.state["percentage"] = 50 + int((chunks_processed / total_chunks) * 40)
            logger.info("[Ingest] Generating embeddings finished ...")

            # 3. Store -----------------------------------------------------------
            if reset:
                logger.info("Resetting collection ...")
                self._store.reset_collection()

            repo_name = os.path.basename(os.path.abspath(directory).rstrip(os.sep))
            active_repo_file = os.path.join(self._store.persist_dir, "active_repo.txt")
            with open(active_repo_file, "w") as f:
                f.write(repo_name)

            ids = [f"{get_display_path(c.file_path)}::{c.start_line}-{c.end_line}" for c in chunks]
            metadatas = [
                {
                    "file_path": get_display_path(c.file_path),
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "language": c.language,
                    "repository": repo_name,
                }
                for c in chunks
            ]

            # We can upsert all at once, Chroma batching takes care of it, but let's update progress
            # The last 10% is storing
            self.state["percentage"] = 95
            
            self._store.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            
            self.state["percentage"] = 100
            self.state["status"] = "completed"

            elapsed = round(time.perf_counter() - t0, 2)
            logger.info("Ingestion complete: %d chunks in %.2fs", len(chunks), elapsed)

            # Generate stats.json
            import json
            from collections import defaultdict
            
            folder_sizes = defaultdict(int)
            for fp in files_list:
                folder = os.path.dirname(fp)
                if folder:
                    folder_sizes[folder] += 1
            largest_folders = sorted([{"name": k, "count": v} for k, v in folder_sizes.items()], key=lambda x: x["count"], reverse=True)[:5]
            
            languages_count = defaultdict(int)
            for c in chunks:
                languages_count[c.language] += 1
            languages = sorted([{"name": k, "count": v} for k, v in languages_count.items()], key=lambda x: x["count"], reverse=True)
            
            folder_count = len(set(os.path.dirname(fp) for fp in files_list if os.path.dirname(fp)))

            stats = {
                "repository_name": repo_name,
                "github_url": github_url or "Local Directory",
                "root_path": os.path.abspath(directory),
                "languages": languages,
                "file_count": files_processed,
                "chunk_count": len(chunks),
                "folder_count": folder_count,
                "last_indexed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "largest_folders": largest_folders,
                "index_duration": f"{elapsed}s",
                "files": files_list
            }
            stats_file = os.path.join(self._store.persist_dir, "stats.json")
            with open(stats_file, "w") as f:
                json.dump(stats, f)

            return IngestionResult(
                chunks_indexed=len(chunks),
                files_processed=files_processed,
                elapsed_seconds=elapsed,
                total_stored=self._store.count,
                files=files_list,
            )
        except Exception as e:
            self.state["status"] = "error"
            logger.exception("Ingestion failed in background task")
            raise e
