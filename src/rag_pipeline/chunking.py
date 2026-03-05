from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChunkStrategy = Literal["char", "paragraph"]


@dataclass
class Chunk:
    doc_id: str
    text: str
    start: int
    end: int


def chunk_text(
    text: str,
    doc_id: str,
    chunk_size: int = 500,
    overlap: int = 100,
    strategy: ChunkStrategy = "char",
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    normalized = " ".join(text.split())
    if not normalized:
        return []

    if strategy == "paragraph":
        return _paragraph_chunks(normalized, doc_id, chunk_size, overlap)
    if strategy == "char":
        return _char_chunks(normalized, doc_id, chunk_size, overlap)

    raise ValueError(f"unsupported chunk strategy: {strategy}")


def _char_chunks(text: str, doc_id: str, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    step = chunk_size - overlap
    for start in range(0, len(text), step):
        end = min(start + chunk_size, len(text))
        snippet = text[start:end].strip()
        if snippet:
            chunks.append(Chunk(doc_id=doc_id, text=snippet, start=start, end=end))
        if end >= len(text):
            break
    return chunks


def _paragraph_chunks(
    text: str, doc_id: str, chunk_size: int, overlap: int
) -> list[Chunk]:
    parts = [p.strip() for p in text.split(". ") if p.strip()]
    chunks: list[Chunk] = []
    current = ""
    start = 0

    for part in parts:
        candidate = f"{current}. {part}" if current else part
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            end = start + len(current)
            chunks.append(Chunk(doc_id=doc_id, text=current, start=start, end=end))
            start = max(0, end - overlap)

        current = part

    if current:
        end = start + len(current)
        chunks.append(Chunk(doc_id=doc_id, text=current, start=start, end=end))

    return chunks
