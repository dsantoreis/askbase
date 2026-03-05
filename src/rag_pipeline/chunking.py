from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    text: str
    start_char: int
    end_char: int


def chunk_text(text: str, doc_id: str, chunk_size: int = 220, overlap: int = 40) -> list[Chunk]:
    if chunk_size < 20:
        raise ValueError("chunk_size must be >= 20")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    words = text.split()
    if not words:
        return []

    normalized = " ".join(words)
    starts: list[int] = []
    cursor = 0
    for word in words:
        starts.append(cursor)
        cursor += len(word) + 1

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    i = 0

    while i < len(words):
        end_idx = min(i + chunk_size, len(words))
        window = words[i:end_idx]
        chunk_txt = " ".join(window)
        start_char = starts[i]
        end_char = start_char + len(chunk_txt)
        chunks.append(Chunk(doc_id=doc_id, text=chunk_txt, start_char=start_char, end_char=end_char))
        if end_idx >= len(words):
            break
        i += step

    assert chunks[-1].end_char <= len(normalized)
    return chunks
