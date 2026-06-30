"""
services/ingestion.py -- Ingestion orchestration service.

Coordinates the full pipeline:
    file discovery -> chunking -> embedding -> ChromaDB storage

Used by both the ``POST /api/v1/ingest`` endpoint and the CLI script.
"""

import logging
import os
import time
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

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
    def __init__(self, embedder: CodeEmbedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store
        self.state_file = os.path.join(self._store.persist_dir, "job_state.json")
        
        # Load and clean up stale state
        self.state = self._load_state()
        if self.state.get("status") == "running":
            # If we restart and find a running state, it means the worker crashed
            self.state["status"] = "failed"
            self.state["error"] = "Ingestion interrupted (worker crashed or restarted)"
            self._save_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": "idle",
            "files_processed": 0,
            "total_files": 0,
            "percentage": 0
        }

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

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
        t0 = time.perf_counter()
        
        self.state = {
            "status": "running",
            "files_processed": 0,
            "total_files": 0,
            "percentage": 0
        }
        self._save_state()
        
        try:
            logger.info("Discovering files in '%s' ...", directory)
            chunker = CodeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            files = chunker.discover_files(directory)
            total_files = len(files)
            
            self.state["total_files"] = total_files
            self._save_state()
            
            if total_files == 0:
                self.state["status"] = "completed"
                self.state["percentage"] = 100
                self._save_state()
                return IngestionResult(0, 0, 0.0, self._store.count, [])

            if reset:
                logger.info("Resetting collection ...")
                self._store.reset_collection()
                
            repo_name = os.path.basename(os.path.abspath(directory).rstrip(os.sep))
            active_repo_file = os.path.join(self._store.persist_dir, "active_repo.txt")
            os.makedirs(os.path.dirname(active_repo_file), exist_ok=True)
            with open(active_repo_file, "w") as f:
                f.write(repo_name)

            def get_display_path(abs_path: str) -> str:
                try:
                    return os.path.relpath(abs_path, directory).replace(os.sep, "/")
                except ValueError:
                    return abs_path

            # Stream processing: process files in small batches to bound memory
            file_batch_size = 20
            total_chunks_processed = 0
            files_processed = 0
            all_chunks_info = []  # Light metadata for stats.json
            files_list = set()
            
            for i in range(0, total_files, file_batch_size):
                file_batch = files[i:i + file_batch_size]
                
                # 1. Chunk batch
                batch_chunks = []
                for fp in file_batch:
                    batch_chunks.extend(chunker.chunk_file(fp))
                    files_list.add(get_display_path(fp))
                
                if not batch_chunks:
                    files_processed += len(file_batch)
                    self.state["files_processed"] = files_processed
                    self.state["percentage"] = int((files_processed / total_files) * 95)
                    self._save_state()
                    continue
                
                # 2. Embed batch
                texts = [c.text for c in batch_chunks]
                embeddings = self._embedder.embed_texts(texts)
                
                # 3. Store batch
                ids = [f"{get_display_path(c.file_path)}::{c.start_line}-{c.end_line}" for c in batch_chunks]
                metadatas = [
                    {
                        "file_path": get_display_path(c.file_path),
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "language": c.language,
                        "repository": repo_name,
                    }
                    for c in batch_chunks
                ]
                
                self._store.upsert(
                    ids=ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                
                # Collect lightweight stats
                for c in batch_chunks:
                    all_chunks_info.append(c.language)
                
                total_chunks_processed += len(batch_chunks)
                files_processed += len(file_batch)
                
                # Update progress (0-95% during processing)
                self.state["files_processed"] = files_processed
                self.state["percentage"] = int((files_processed / total_files) * 95)
                self._save_state()
                
                logger.info(f"Processed batch {i} to {i + len(file_batch)} ({files_processed}/{total_files} files)")

            self.state["percentage"] = 100
            self.state["status"] = "completed"
            self._save_state()

            elapsed = round(time.perf_counter() - t0, 2)
            logger.info("Ingestion complete: %d chunks in %.2fs", total_chunks_processed, elapsed)

            # Generate stats.json
            from collections import defaultdict
            files_list = list(files_list)
            folder_sizes = defaultdict(int)
            for fp in files_list:
                folder = os.path.dirname(fp)
                if folder:
                    folder_sizes[folder] += 1
            largest_folders = sorted([{"name": k, "count": v} for k, v in folder_sizes.items()], key=lambda x: x["count"], reverse=True)[:5]
            
            languages_count = defaultdict(int)
            for lang in all_chunks_info:
                languages_count[lang] += 1
            languages = sorted([{"name": k, "count": v} for k, v in languages_count.items()], key=lambda x: x["count"], reverse=True)
            
            folder_count = len(set(os.path.dirname(fp) for fp in files_list if os.path.dirname(fp)))

            stats = {
                "repository_name": repo_name,
                "github_url": github_url or "Local Directory",
                "root_path": os.path.abspath(directory),
                "languages": languages,
                "file_count": files_processed,
                "chunk_count": total_chunks_processed,
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
                chunks_indexed=total_chunks_processed,
                files_processed=files_processed,
                elapsed_seconds=elapsed,
                total_stored=self._store.count,
                files=files_list,
            )
        except Exception as e:
            self.state["status"] = "failed"
            self.state["error"] = str(e)
            self._save_state()
            logger.exception("Ingestion failed in background task")
            raise e
