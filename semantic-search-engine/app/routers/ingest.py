"""
routers/ingest.py -- Ingestion API endpoint.

POST /api/v1/ingest
    Accepts a local directory path, runs the full ingestion pipeline
    (chunk -> embed -> store), and returns a summary.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, status

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from app.config import get_settings
from app.models import IngestRequest, IngestResponse, IngestStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Ingestion"])


def background_ingest(
    service,
    github_url: str | None,
    directory: str | None,
    chunk_size: int,
    chunk_overlap: int,
    reset: bool,
    data_dir: str
):
    try:
        service.state = {
            "status": "running",
            "files_processed": 0,
            "total_files": 0,
            "percentage": 0
        }
        
        if github_url:
            import subprocess
            from urllib.parse import urlparse
            
            parsed = urlparse(github_url)
            path_parts = parsed.path.strip('/').split('/')
            repo_name = path_parts[-1] if path_parts else "repo"
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
                
            target_dir = os.path.join(data_dir, "github", repo_name)
            
            if not os.path.exists(target_dir):
                os.makedirs(os.path.dirname(target_dir), exist_ok=True)
                subprocess.run(["git", "clone", github_url, target_dir], check=True, capture_output=True)
            else:
                try:
                    subprocess.run(["git", "pull"], cwd=target_dir, check=True, capture_output=True)
                except Exception:
                    pass
            directory = target_dir
        else:
            directory = os.path.abspath(directory)
            
        service.ingest_directory(
            directory=directory,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            reset=reset,
            github_url=github_url
        )
    except Exception as e:
        service.state["status"] = "error"
        logger.exception(f"Background ingestion failed: {e}")

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest code files asynchronously",
)
async def ingest_directory_endpoint(body: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    from app.main import get_ingestion_service

    settings = get_settings()
    service = get_ingestion_service()

    if not body.directory and not body.github_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either directory or github_url.",
        )

    chunk_size = body.chunk_size or settings.chunk_size
    chunk_overlap = body.chunk_overlap or settings.chunk_overlap

    if chunk_overlap >= chunk_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_overlap must be smaller than chunk_size.",
        )

    background_tasks.add_task(
        background_ingest,
        service=service,
        github_url=body.github_url,
        directory=body.directory,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        reset=body.reset,
        data_dir=settings.data_dir
    )

    return IngestResponse(
        success=True,
        message="Repository ingestion started."
    )

@router.get(
    "/ingest/status",
    response_model=IngestStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ingestion status",
)
async def get_ingest_status() -> IngestStatusResponse:
    from app.main import get_ingestion_service
    service = get_ingestion_service()
    state = service.get_status()
    
    # If finished, API requires exactly {"status": "completed"}
    if state["status"] == "completed":
        return IngestStatusResponse(status="completed", files_processed=state["files_processed"], total_files=state["total_files"], percentage=100)
        
    return IngestStatusResponse(**state)

@router.get(
    "/repo/stats",
    status_code=status.HTTP_200_OK,
    summary="Get repository statistics",
)
async def get_repo_stats():
    from app.config import get_settings
    settings = get_settings()
    stats_file = os.path.join(settings.chroma_persist_dir, "stats.json")
    
    if not os.path.exists(stats_file):
        raise HTTPException(status_code=404, detail="No repository has been indexed yet.")
        
    import json
    with open(stats_file, "r") as f:
        return json.load(f)

@router.get(
    "/repo/file",
    status_code=status.HTTP_200_OK,
    summary="Get file content",
)
async def get_repo_file(path: str):
    from app.config import get_settings
    settings = get_settings()
    stats_file = os.path.join(settings.chroma_persist_dir, "stats.json")
    
    if not os.path.exists(stats_file):
        raise HTTPException(status_code=404, detail="No repository has been indexed yet.")
        
    import json
    import os
    with open(stats_file, "r") as f:
        stats = json.load(f)
        
    root_path = stats.get("root_path")
    if not root_path:
        raise HTTPException(status_code=400, detail="Repository root path not found.")
        
    full_path = os.path.normpath(os.path.join(root_path, path))
    # Security check: ensure the requested path is within the root_path
    if not full_path.startswith(os.path.normpath(root_path)):
        raise HTTPException(status_code=403, detail="Access denied.")
        
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found.")
        
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"path": path, "content": content}
    except UnicodeDecodeError:
        return {"path": path, "content": "Binary file cannot be displayed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


