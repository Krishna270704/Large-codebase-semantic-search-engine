"""
services/rag.py -- Retrieval-Augmented Generation pipeline.

Orchestrates the full RAG flow using Gemini:
1. Embed the user question.
2. Retrieve the top-k most relevant code chunks from ChromaDB.
3. Build a grounded context block from the retrieved chunks.
4. Prompt Gemini with system instructions, history, context, and question.
5. Return (or stream) the generated answer together with source citations.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional

# (old google.generativeai removed)

from app.services.embedder import CodeEmbedder
from app.services.vectordb import SearchResult, VectorStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RAG_TOP_K = 10

NO_CONTEXT_ANSWER = (
    "I could not find relevant information in the codebase. "
    "Try rephrasing your question, or make sure the relevant files have "
    "been ingested via POST /api/v1/ingest."
)

import asyncio
import time
from google import genai

# Lazy initialization of Gemini client
_client = None

def get_genai_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not configured.")
        _client = genai.Client(api_key=api_key)
    return _client

class RAGException(Exception):
    def __init__(self, message, sources=None):
        super().__init__(message)
        self.sources = sources or []

def is_retryable_error(exc: Exception) -> bool:
    err_str = str(exc)
    return any(code in err_str for code in ["429", "500", "502", "503", "504"])



# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RAGSource:
    file_path: str
    relative_path: str
    start_line: int
    end_line: int
    language: str
    score: float
    snippet: str
    reason: str = ""
    repository_name: str = ""


@dataclass
class RAGResult:
    question: str
    answer: str
    sources: List[RAGSource] = field(default_factory=list)
    model: str = "gemini-1.5-flash"
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# RAG Service
# ---------------------------------------------------------------------------

class RAGService:
    def __init__(
        self,
        embedder: CodeEmbedder,
        store: VectorStore,
        top_k: int = DEFAULT_RAG_TOP_K,
        **kwargs
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._top_k = top_k
        self._model = "gemini-1.5-flash"
        self._active_repo = ""
        logger.info("RAGService ready (model=%s, top_k=%d)", self._model, top_k)

    def _get_active_repo_name(self) -> str:
        active_repo_file = os.path.join(self._store.persist_dir, "active_repo.txt")
        if os.path.exists(active_repo_file):
            with open(active_repo_file, "r") as f:
                return f.read().strip()
        return ""

    @staticmethod
    def _get_relative_dir(file_path: str) -> str:
        parts = file_path.replace("\\", "/").rsplit("/", 1)
        return parts[0] if len(parts) > 1 else "/"

    def _retrieve(self, question: str) -> List[SearchResult]:
        if self._store.count == 0:
            logger.warning("Vector store is empty — no context to retrieve.")
            return []
            
        active_repo_file = os.path.join(self._store.persist_dir, "active_repo.txt")
        where_filter = None
        if os.path.exists(active_repo_file):
            with open(active_repo_file, "r") as f:
                repo_name = f.read().strip()
                if repo_name:
                    where_filter = {"repository": repo_name}
                    logger.info("Verifying correct repository context: %s", repo_name)

        query_embedding = self._embedder.embed_query(question)
        hits = self._store.search(query_embedding, top_k=self._top_k, where=where_filter)
        logger.info("Retrieved %d chunks for question: %.80s…", len(hits), question)
        return hits

    @staticmethod
    def _format_context(hits: List[SearchResult]) -> str:
        if not hits:
            return "(No relevant code context was found.)"

        blocks = []
        for i, hit in enumerate(hits, 1):
            header = f"[File: {hit.file_path} | Lines: {hit.start_line}–{hit.end_line}]"
            blocks.append(f"{header}\n```{hit.language}\n{hit.text}\n```")

        return "\n\n".join(blocks)

    @staticmethod
    def _build_prompt(question: str, context: str, history_context: str = "") -> str:
        prompt = f"""
You are an AI codebase assistant.

Answer ONLY using the given context.
If the answer is not in the context, say "I don't know".

Context:
{context}
{history_context}
Question:
{question}

Answer:
"""
        return prompt.strip()

    def _hits_to_sources(self, hits: List[SearchResult]) -> List[RAGSource]:
        repo = self._get_active_repo_name()
        return [
            RAGSource(
                file_path=h.file_path,
                relative_path=self._get_relative_dir(h.file_path),
                start_line=h.start_line,
                end_line=h.end_line,
                language=h.language,
                score=h.score,
                snippet=h.text,
                repository_name=repo,
            )
            for h in hits
        ]

    async def _rerank_and_explain(self, question: str, hits: List[SearchResult]) -> List[RAGSource]:
        # Deduplicate chunks based on file_path and text snippet
        unique_hits = []
        seen = set()
        for hit in hits:
            key = (hit.file_path, hit.text.strip())
            if key not in seen:
                seen.add(key)
                unique_hits.append(hit)
        
        # Only rerank up to 10 unique hits
        unique_hits = unique_hits[:10]
        
        if not unique_hits:
            return []
            
        chunks_json = []
        for i, hit in enumerate(unique_hits):
            chunks_json.append({
                "index": i,
                "file_path": hit.file_path,
                "content": hit.text
            })
            
        prompt = f"""
You are a reranking engine. Given the user's question and a list of retrieved code chunks, 
evaluate each chunk's relevance to the question.

Question: {question}

Chunks:
{json.dumps(chunks_json, indent=2)}

Select the most relevant chunks (up to 5). Return ONLY a JSON array of objects with this exact structure:
[
  {{
    "index": <integer index from the chunks list>,
    "reason": "<short 1-sentence reason why this chunk is highly relevant>"
  }}
]
Do not return markdown formatting (no ```json), just the raw JSON array.
"""
        try:
            logger.info(f"Calling Gemini ({self._model}) for reranking {len(unique_hits)} chunks...")
            start_t = time.time()
            response = await get_genai_client().aio.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3]
            
            selected_info = json.loads(raw_text.strip())
            
            reranked_sources = []
            for item in selected_info:
                idx = item.get("index")
                if isinstance(idx, int) and 0 <= idx < len(unique_hits):
                    h = unique_hits[idx]
                    reranked_sources.append(
                        RAGSource(
                            file_path=h.file_path,
                            relative_path=self._get_relative_dir(h.file_path),
                            start_line=h.start_line,
                            end_line=h.end_line,
                            language=h.language,
                            score=h.score,
                            snippet=h.text,
                            reason=item.get("reason", "Highly relevant code."),
                            repository_name=self._get_active_repo_name(),
                        )
                    )
            logger.info(f"LLM Reranker selected {len(reranked_sources)} chunks out of {len(unique_hits)}. (Latency: {time.time() - start_t:.2f}s)")
            return reranked_sources
        except Exception as e:
            logger.warning(f"Reranking failed: {e}. Falling back to top 5.")
            repo = self._get_active_repo_name()
            return [
                RAGSource(
                    file_path=h.file_path,
                    relative_path=self._get_relative_dir(h.file_path),
                    start_line=h.start_line,
                    end_line=h.end_line,
                    language=h.language,
                    score=h.score,
                    snippet=h.text,
                    reason="Relevant based on vector similarity.",
                    repository_name=repo,
                ) for h in unique_hits[:5]
            ]

    async def _rewrite_query(self, question: str, history: List[Dict[str, str]]) -> str:
        if not history:
            return question
            
        history_text = "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history[-6:]])
        prompt = f"""Given the following conversation history and the user's latest follow-up question, rewrite the follow-up question to be a standalone query that can be used to search a codebase.
If the latest question is already standalone, return it exactly as is. Do not answer it, just rewrite it.

History:
{history_text}

Latest question: {question}

Standalone query:"""
        try:
            logger.info(f"Calling Gemini ({self._model}) to rewrite query based on history...")
            start_t = time.time()
            response = await get_genai_client().aio.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            rewritten = response.text.strip()
            logger.info(f"Rewrote query: '{question}' -> '{rewritten}' (Latency: {time.time() - start_t:.2f}s)")
            return rewritten
        except Exception as e:
            logger.warning(f"Failed to rewrite query: {e}")
            return question

    async def _summarize_history(self, history: List[Dict[str, str]]) -> str:
        history_text = "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history])
        prompt = f"Summarize the following conversation concisely, focusing on the main technical points discussed. This will be used as context for the AI. \n\n{history_text}\n\nSummary:"
        try:
            logger.info(f"Calling Gemini ({self._model}) to summarize history...")
            start_t = time.time()
            response = await get_genai_client().aio.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            summary = response.text.strip()
            logger.info(f"Automatically summarized long conversation. (Latency: {time.time() - start_t:.2f}s)")
            return summary
        except Exception as e:
            logger.warning(f"Failed to summarize history: {e}")
            return history_text

    async def answer(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> RAGResult:
        logger.info(f"User question: {question}")
        
        search_query = question
        history_context = ""
        
        if history:
            search_query = await self._rewrite_query(question, history)
            
            if len(history) > 6:
                summary = await self._summarize_history(history)
                history_context = f"\nConversation Summary:\n{summary}\n"
            else:
                history_context = "\nHistory:\n" + "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history]) + "\n"

        hits = self._retrieve(search_query)
        
        # Display retrieved files and similarity scores for debugging
        for i, h in enumerate(hits):
            logger.info(f"Retrieved chunk {i+1}: {h.file_path} - Score: {h.score:.4f}")

        if not hits:
            return RAGResult(
                question=question,
                answer=NO_CONTEXT_ANSWER,
                sources=[],
                model=self._model,
            )
            
        # Check low similarity threshold
        if hits[0].score < 0.2:
            return RAGResult(
                question=question,
                answer="The indexed repository does not appear to contain enough information to answer this question.",
                sources=self._hits_to_sources(hits),
                model=self._model,
            )
            
        # Reranking step: Deduplicate and select top chunks with reasons using LLM
        sources = await self._rerank_and_explain(search_query, hits)
        logger.info(f"Retrieved chunk count (post-rerank): {len(sources)}")
        
        # Build context from the reranked sources
        # We need to map sources back to SearchResult for format_context, or just format sources directly
        context_blocks = []
        for i, s in enumerate(sources, 1):
            header = f"[File: {s.file_path} | Lines: {s.start_line}–{s.end_line}]"
            context_blocks.append(f"{header}\n```{s.language}\n{s.snippet}\n```")
        context = "\n\n".join(context_blocks)
        
        prompt = self._build_prompt(question, context, history_context)
        
        logger.info(f"Final prompt sent to Gemini:\n{prompt}")
        logger.info(f"Prompt length: {len(prompt)} characters")
        logger.info(f"Selected model: {self._model}")

        retries = 3
        backoff = [2, 4, 8]
        answer_text = ""
        
        start_time = time.time()
        for attempt in range(retries + 1):
            try:
                response = await get_genai_client().aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                )
                answer_text = response.text
                logger.info(f"Final status: success after {attempt} retries")
                break
            except Exception as exc:
                if attempt < retries and is_retryable_error(exc):
                    logger.warning(f"Retryable error: {exc}. Retry attempts: {attempt + 1}. Retrying in {backoff[attempt]} seconds...")
                    await asyncio.sleep(backoff[attempt])
                else:
                    latency = time.time() - start_time
                    logger.error(f"LLM call failed. Final status: error. Gemini latency: {latency:.2f}s")
                    raise RAGException(str(exc), sources=sources)
        
        latency = time.time() - start_time
        logger.info(f"Gemini latency: {latency:.2f}s")

        return RAGResult(
            question=question,
            answer=answer_text,
            sources=sources,
            model=self._model,
        )

    async def stream_answer(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        try:
            logger.info(f"User question: {question}")
            
            search_query = question
            history_context = ""
            
            if history:
                search_query = await self._rewrite_query(question, history)
                
                if len(history) > 6:
                    summary = await self._summarize_history(history)
                    history_context = f"\nConversation Summary:\n{summary}\n"
                else:
                    history_context = "\nHistory:\n" + "\n".join([f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in history]) + "\n"

            hits = self._retrieve(search_query)
            
            for i, h in enumerate(hits):
                logger.info(f"Retrieved chunk {i+1}: {h.file_path} - Score: {h.score:.4f}")

            if not hits:
                sources_payload = {"type": "sources", "sources": []}
                yield f"data: {json.dumps(sources_payload)}\n\n"
                
                no_ctx = {"type": "token", "content": NO_CONTEXT_ANSWER}
                yield f"data: {json.dumps(no_ctx)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': self._model})}\n\n"
                yield "data: [DONE]\n\n"
                return
                
            if hits[0].score < 0.2:
                sources = self._hits_to_sources(hits)
                sources_payload = {
                    "type": "sources",
                    "sources": [
                        {
                            "file_path": s.file_path,
                            "start_line": s.start_line,
                            "end_line": s.end_line,
                            "language": s.language,
                            "score": s.score,
                            "snippet": s.snippet,
                        }
                        for s in sources
                    ],
                }
                yield f"data: {json.dumps(sources_payload)}\n\n"
                msg = {"type": "token", "content": "The indexed repository does not appear to contain enough information to answer this question."}
                yield f"data: {json.dumps(msg)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model': self._model})}\n\n"
                yield "data: [DONE]\n\n"
                return
                
            # Reranking step: Deduplicate and select top chunks with reasons using LLM
            sources = await self._rerank_and_explain(search_query, hits)
            
            logger.info(f"Retrieved chunk count (post-rerank): {len(sources)}")

            sources_payload = {
                "type": "sources",
                "sources": [
                    {
                        "file_path": s.file_path,
                        "relative_path": s.relative_path,
                        "start_line": s.start_line,
                        "end_line": s.end_line,
                        "language": s.language,
                        "score": s.score,
                        "snippet": s.snippet,
                        "reason": s.reason,
                        "repository_name": s.repository_name,
                    }
                    for s in sources
                ],
            }
            yield f"data: {json.dumps(sources_payload)}\n\n"

            context_blocks = []
            for i, s in enumerate(sources, 1):
                header = f"[File: {s.file_path} | Lines: {s.start_line}–{s.end_line}]"
                context_blocks.append(f"{header}\n```{s.language}\n{s.snippet}\n```")
            context = "\n\n".join(context_blocks)
            
            prompt = self._build_prompt(question, context, history_context)
            
            logger.info(f"Final prompt sent to Gemini:\n{prompt}")
            logger.info(f"Prompt length: {len(prompt)} characters")
            logger.info(f"Selected model: {self._model}")
            
            retries = 3
            backoff = [2, 4, 8]
            
            start_time = time.time()
            for attempt in range(retries + 1):
                try:
                    # Using generate_content async/streaming
                    response = await get_genai_client().aio.models.generate_content_stream(
                        model=self._model,
                        contents=prompt,
                    )
                    async for chunk in response:
                        if chunk.text:
                            token_event = {"type": "token", "content": chunk.text}
                            yield f"data: {json.dumps(token_event)}\n\n"
                    
                    logger.info(f"Final status: success after {attempt} retries")
                    break
                except Exception as exc:
                    if attempt < retries and is_retryable_error(exc):
                        logger.warning(f"Retryable error: {exc}. Retry attempts: {attempt + 1}. Retrying in {backoff[attempt]} seconds...")
                        await asyncio.sleep(backoff[attempt])
                    else:
                        latency = time.time() - start_time
                        logger.error(f"LLM streaming failed. Final status: error. Gemini latency: {latency:.2f}s")
                        error_event = {
                            "type": "error",
                            "content": f"The AI service is temporarily busy. Please try again in a few seconds.",
                        }
                        yield f"data: {json.dumps(error_event)}\n\n"
                        break
            
            latency = time.time() - start_time
            logger.info(f"Gemini latency: {latency:.2f}s")

            done_event = {"type": "done", "model": self._model}
            yield f"data: {json.dumps(done_event)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("Global exception during RAG stream processing")
            # If an exception is raised before headers are sent, yield will force a 200 OK + this error chunk
            error_event = {
                "type": "error",
                "content": f"An unexpected error occurred during processing: {str(e)}"
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            yield "data: [DONE]\n\n"
