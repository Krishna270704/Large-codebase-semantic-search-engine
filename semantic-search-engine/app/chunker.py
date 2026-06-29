"""
chunker.py — Code-aware file chunking logic.

Splits source code files into overlapping chunks of ~300–500 tokens,
preserving file path, line numbers, and inferred language metadata.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import tiktoken


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".html": "html",
    ".css": "css",
    ".txt": "text",
    ".md": "markdown",
    ".ipynb": "jupyter",
}

IGNORED_DIRS: set[str] = {".git", "node_modules", "__pycache__", ".venv", "venv"}

DEFAULT_CHUNK_SIZE = 400       # target tokens per chunk
DEFAULT_CHUNK_OVERLAP = 50     # overlap tokens between consecutive chunks


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodeChunk:
    """Represents a single chunk of code with its metadata."""

    text: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    token_count: int = 0

    @property
    def chunk_id(self) -> str:
        """Deterministic ID derived from file path and line range."""
        safe_path = self.file_path.replace(os.sep, "_").replace("/", "_")
        return f"{safe_path}::{self.start_line}-{self.end_line}"


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

class CodeChunker:
    """Splits source files into overlapping, token-counted chunks.

    Parameters
    ----------
    chunk_size : int
        Target number of tokens per chunk (default 400).
    chunk_overlap : int
        Number of overlapping tokens between consecutive chunks (default 50).
    encoding_name : str
        Tiktoken encoding used for token counting (default ``cl100k_base``).
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        encoding_name: str = "cl100k_base",
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._enc = tiktoken.get_encoding(encoding_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover_files(self, root_dir: str) -> List[str]:
        """Recursively discover supported source files under *root_dir*.

        Skips directories listed in ``IGNORED_DIRS``.
        """
        root = Path(root_dir).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Directory not found: {root}")

        discovered: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune ignored directories in-place so os.walk won't descend
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    discovered.append(os.path.join(dirpath, fname))

        return sorted(discovered)

    def chunk_file(self, file_path: str) -> List[CodeChunk]:
        """Read a single file and return a list of ``CodeChunk`` objects."""
        ext = os.path.splitext(file_path)[1].lower()
        language = SUPPORTED_EXTENSIONS.get(ext, "unknown")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                if ext == ".ipynb":
                    import json
                    try:
                        nb = json.load(fh)
                        lines = []
                        for cell in nb.get("cells", []):
                            if cell.get("cell_type") in ("code", "markdown"):
                                source = cell.get("source", [])
                                if isinstance(source, str):
                                    lines.extend(source.splitlines(True))
                                else:
                                    lines.extend(source)
                                lines.append("\n\n")
                    except Exception as e:
                        print(f"[WARN] Failed to parse notebook {file_path}: {e}")
                        fh.seek(0)
                        lines = fh.readlines()
                else:
                    lines = fh.readlines()
        except OSError as exc:
            print(f"[WARN] Could not read {file_path}: {exc}")
            return []

        if not lines:
            return []

        return self._split_lines_into_chunks(lines, file_path, language)

    def chunk_directory(self, root_dir: str) -> List[CodeChunk]:
        """Convenience: discover + chunk every file under *root_dir*."""
        files = self.discover_files(root_dir)
        all_chunks: List[CodeChunk] = []
        for fp in files:
            all_chunks.extend(self.chunk_file(fp))
        return all_chunks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def _split_lines_into_chunks(
        self,
        lines: List[str],
        file_path: str,
        language: str,
    ) -> List[CodeChunk]:
        """Split a list of lines into overlapping chunks based on token count."""
        chunks: List[CodeChunk] = []
        total_lines = len(lines)
        start_idx = 0  # 0-based index into `lines`

        while start_idx < total_lines:
            # Accumulate lines until we hit the chunk_size token budget
            current_text = ""
            end_idx = start_idx

            while end_idx < total_lines:
                candidate = current_text + lines[end_idx]
                token_count = self._count_tokens(candidate)
                if token_count > self.chunk_size and current_text:
                    # Adding this line would exceed budget → stop before it
                    break
                current_text = candidate
                end_idx += 1

            # Guard against a single enormous line exceeding the budget
            if not current_text:
                current_text = lines[start_idx]
                end_idx = start_idx + 1

            token_count = self._count_tokens(current_text)

            chunks.append(
                CodeChunk(
                    text=current_text,
                    file_path=file_path,
                    start_line=start_idx + 1,          # 1-based for display
                    end_line=end_idx,                   # inclusive 1-based
                    language=language,
                    token_count=token_count,
                )
            )

            if end_idx >= total_lines:
                break

            # Advance start, accounting for overlap
            step = max(1, end_idx - start_idx - self._overlap_lines(lines, start_idx, end_idx))
            start_idx += step

        return chunks

    def _overlap_lines(self, lines: List[str], start: int, end: int) -> int:
        """Determine how many trailing lines correspond to ~chunk_overlap tokens."""
        overlap_tokens = 0
        overlap_lines = 0
        for idx in range(end - 1, start - 1, -1):
            overlap_tokens += self._count_tokens(lines[idx])
            overlap_lines += 1
            if overlap_tokens >= self.chunk_overlap:
                break
        return overlap_lines
