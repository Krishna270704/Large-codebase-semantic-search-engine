"""
routers/ask.py -- RAG Q&A endpoint.

POST /api/v1/ask
    Accepts a natural-language question about the codebase, retrieves
    relevant code chunks, and generates a grounded answer using an LLM.

    Supports two response modes:
    * **Streaming** (default, ``stream: true``):  Returns Server-Sent Events
      with token-by-token output.
    * **JSON** (``stream: false``):  Returns a single ``AskResponse`` payload.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models import AskRequest, AskResponse, AskSourceItem, ExplainRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Q&A (RAG)"])


@router.post(
    "/ask",
    summary="Ask a question about the codebase (RAG)",
    description=(
        "Accepts a natural-language question and returns a generated answer "
        "grounded in relevant code snippets retrieved from the indexed codebase.\n\n"
        "**Streaming mode** (default): Returns `text/event-stream` with SSE events:\n"
        "- `{type: 'sources', sources: [...]}` — retrieved code chunks\n"
        "- `{type: 'token', content: '...'}` — incremental answer tokens\n"
        "- `{type: 'done', model: '...'}` — completion signal\n"
        "- `data: [DONE]` — stream terminator\n\n"
        "**JSON mode** (`stream: false`): Returns a single `AskResponse` object."
    ),
    responses={
        200: {
            "description": "Successful response (JSON or SSE stream).",
            "content": {
                "application/json": {
                    "schema": AskResponse.model_json_schema(),
                },
                "text/event-stream": {
                    "schema": {"type": "string"},
                },
            },
        },
    },
)
async def ask_question(body: AskRequest):
    """Run the RAG pipeline and return an answer with source citations.

    The endpoint operates in two modes based on ``body.stream``:

    * **Streaming** — returns a ``text/event-stream`` response.
      Each event is a JSON object prefixed with ``data: ``.
    * **JSON** — returns a standard ``AskResponse`` payload.
    """
    from app.main import get_rag_service

    try:
        rag = get_rag_service()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "RAG service is not available. "
                "Make sure GEMINI_API_KEY is set in your .env file."
            ),
        )

    logger.info("Ask endpoint called (stream=%s): %s", body.stream, body.question)

    # Convert history from Pydantic models to plain dicts
    history = [msg.model_dump() for msg in body.history] if body.history else None

    # ── Streaming mode ────────────────────────────────────────────────
    if body.stream:
        return StreamingResponse(
            rag.stream_answer(question=body.question, history=history),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # disable nginx buffering
            },
        )

    # ── JSON mode ─────────────────────────────────────────────────────
    from fastapi.responses import JSONResponse
    
    try:
        result = await rag.answer(question=body.question, history=history)
        
        return AskResponse(
            question=result.question,
            answer=result.answer,
            sources=[
                AskSourceItem(
                    file_path=s.file_path,
                    start_line=s.start_line,
                    end_line=s.end_line,
                    language=s.language,
                    score=s.score,
                    snippet=s.snippet,
                )
                for s in result.sources
            ],
            model=result.model,
            tokens_used=result.tokens_used,
        )
    except Exception as exc:
        logger.exception("RAG pipeline failed")
        
        # We try to get sources if they were attached to the exception, or just return empty for now.
        # But wait, the RAG pipeline is resilient, we can extract the sources before calling LLM.
        # Actually, if we want to return sources, we need them from the exception or we modify rag.py to attach them.
        # Let's assume rag.py raises an exception with a .sources attribute if it fails during LLM call.
        
        sources_to_return = []
        if hasattr(exc, "sources") and exc.sources:
            sources_to_return = [
                {
                    "file_path": s.file_path,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "language": s.language,
                    "score": s.score,
                    "snippet": s.snippet,
                }
                for s in exc.sources
            ]

        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": str(exc),
                "retryable": True,
                "sources": sources_to_return
            }
        )

@router.post(
    "/explain",
    summary="Explain a specific file or code snippet",
    description="Uses Gemini to explain the purpose, architecture, and complexity of a file.",
)
async def explain_file_endpoint(body: ExplainRequest):
    from app.main import get_rag_service
    import os

    try:
        rag = get_rag_service()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="RAG service not available.")
        
    prompt = f"""
You are an expert AI codebase assistant. 
Please explain the following file/snippet: `{body.file_path}`

Focus your explanation on:
- Purpose
- Architecture
- Main classes
- Functions
- Dependencies
- Execution flow
- Improvements
- Complexity

Code:
```
{body.snippet}
```
"""
    
    # Try to find the full file if possible, but fallback to snippet
    # Since we don't have the absolute path easily, we just use snippet as context for now,
    # or the user can send the full file context if needed. The snippet is usually large enough.

    if body.stream:
        async def stream_explanation():
            from google import genai
            import json
            import time
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            
            try:
                response = await client.aio.models.generate_content_stream(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                async for chunk in response:
                    if chunk.text:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
                
        return StreamingResponse(
            stream_explanation(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    else:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            from fastapi.responses import JSONResponse
            return JSONResponse({"explanation": response.text})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


