from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    doc_id: str
    text: str
    start: int
    end: int


def chunk_text(text: str, doc_id: str, chunk_size: int = 500, overlap: int = 100) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    text = " ".join(text.split())
    if not text:
        return []

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
