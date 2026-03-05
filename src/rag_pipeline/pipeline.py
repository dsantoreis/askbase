from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .chunking import Chunk, chunk_text
from .documents import collect_documents
from .retrieval import RetrievedChunk, Retriever


@dataclass(frozen=True)
class Citation:
    doc_id: str
    start_char: int
    end_char: int
    score: float
    excerpt: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation]


class RAGPipeline:
    INDEX_VERSION = "3.0"

    def __init__(self, chunk_size: int = 220, overlap: int = 40) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: list[Chunk] = []
        self.retriever = Retriever()

    def ingest(self, paths: list[str | Path]) -> int:
        docs = collect_documents(paths)
        chunks: list[Chunk] = []
        for doc_id, text in docs.items():
            chunks.extend(
                chunk_text(text=text, doc_id=doc_id, chunk_size=self.chunk_size, overlap=self.overlap)
            )
        self.chunks = chunks
        self.retriever.fit(chunks)
        return len(chunks)

    def ask(self, query: str, top_k: int = 3) -> Answer:
        hits = self.retrieve(query=query, top_k=top_k)
        if not hits:
            return Answer(text="No supporting context found.", citations=[])

        lines = ["Answer grounded in retrieved context:"]
        citations: list[Citation] = []
        for idx, hit in enumerate(hits, start=1):
            excerpt = hit.chunk.text[:200]
            lines.append(f"[{idx}] {excerpt}")
            citations.append(
                Citation(
                    doc_id=hit.chunk.doc_id,
                    start_char=hit.chunk.start_char,
                    end_char=hit.chunk.end_char,
                    score=round(hit.score, 4),
                    excerpt=excerpt,
                )
            )
        return Answer(text="\n".join(lines), citations=citations)

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        return self.retriever.search(self.chunks, query=query, top_k=top_k)

    def save(self, path: str | Path) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as fh:
            pickle.dump(
                {
                    "index_version": self.INDEX_VERSION,
                    "chunk_size": self.chunk_size,
                    "overlap": self.overlap,
                    "chunks": self.chunks,
                    "vectorizer": self.retriever.vectorizer,
                    "matrix": self.retriever._matrix,
                },
                fh,
            )

    @classmethod
    def load(cls, path: str | Path) -> "RAGPipeline":
        with Path(path).open("rb") as fh:
            payload = pickle.load(fh)
        if payload.get("index_version") != cls.INDEX_VERSION:
            raise ValueError("index version mismatch")
        rag = cls(chunk_size=payload["chunk_size"], overlap=payload["overlap"])
        rag.chunks = payload["chunks"]
        rag.retriever.vectorizer = payload["vectorizer"]
        rag.retriever._matrix = payload["matrix"]
        return rag


def citations_to_dict(citations: list[Citation]) -> list[dict[str, Any]]:
    return [asdict(c) for c in citations]


def dump_eval(path: str | Path, rows: list[dict[str, Any]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
