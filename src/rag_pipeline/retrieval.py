from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunking import Chunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


class Retriever:
    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self._matrix = None

    def fit(self, chunks: list[Chunk]) -> None:
        texts = [c.text for c in chunks]
        self._matrix = self.vectorizer.fit_transform(texts) if texts else None

    def search(self, chunks: list[Chunk], query: str, top_k: int = 3) -> list[RetrievedChunk]:
        if not query.strip() or not chunks or self._matrix is None:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(
            [RetrievedChunk(chunk=chunk, score=float(scores[idx])) for idx, chunk in enumerate(chunks)],
            key=lambda item: item.score,
            reverse=True,
        )
        return ranked[:top_k]
