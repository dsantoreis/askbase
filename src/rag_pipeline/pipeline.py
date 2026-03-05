from __future__ import annotations

import hashlib
import json
import logging
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunking import Chunk, ChunkStrategy, chunk_text

logger = logging.getLogger(__name__)


@dataclass
class IngestConfig:
    chunk_size: int = 500
    overlap: int = 100
    chunk_strategy: ChunkStrategy = "char"
    max_file_mb: int = 5
    min_chars: int = 30


@dataclass
class RetrievalConfig:
    lexical_weight: float = 0.7
    keyword_weight: float = 0.3
    semantic_weight: float = 0.0
    rerank_boost: float = 0.15
    use_semantic: bool = False
    semantic_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class Citation:
    doc_id: str
    chunk_start: int
    chunk_end: int
    score: float
    excerpt: str


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]


class RAGPipeline:
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}
    INDEX_VERSION = "2.2"

    def __init__(
        self,
        ingest_config: IngestConfig | None = None,
        retrieval_config: RetrievalConfig | None = None,
    ) -> None:
        self.ingest_config = ingest_config or IngestConfig()
        self.retrieval_config = retrieval_config or RetrievalConfig()
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.chunks: list[Chunk] = []
        self._matrix: Any = None
        self._doc_hashes: dict[str, str] = {}
        self._semantic_model: Any = None
        self._semantic_embeddings: Any = None

    def ingest_paths(self, paths: list[str | Path]) -> int:
        all_chunks: list[Chunk] = []
        seen_hashes: set[str] = set()

        for path in paths:
            p = Path(path)
            if p.is_dir():
                for file in sorted(p.rglob("*")):
                    if (
                        file.is_file()
                        and file.suffix.lower() in self.SUPPORTED_EXTENSIONS
                    ):
                        all_chunks.extend(self._read_and_chunk(file, seen_hashes))
            elif p.is_file():
                all_chunks.extend(self._read_and_chunk(p, seen_hashes))
            else:
                logger.warning("invalid_path", extra={"path": str(path)})

        self.chunks = all_chunks
        texts = [c.text for c in self.chunks]
        self._matrix = self.vectorizer.fit_transform(texts) if texts else None
        self._semantic_embeddings = self._encode_semantic_texts(texts)
        logger.info("ingest_complete", extra={"chunks": len(self.chunks)})
        return len(self.chunks)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
        doc_id: str | None = None,
        doc_id_contains: str | None = None,
    ) -> list[dict[str, Any]]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if min_score < 0:
            raise ValueError("min_score must be >= 0")
        normalized_doc_id = doc_id.strip().lower() if doc_id else ""
        normalized_doc_filter = doc_id_contains.strip().lower() if doc_id_contains else ""
        if not query.strip() or self._matrix is None or not self.chunks:
            return []

        qv = self.vectorizer.transform([query])
        lexical_scores = cosine_similarity(qv, self._matrix)[0]
        semantic_scores = self._semantic_similarity(query)
        query_terms = set(_normalize_terms(query))

        ranked: list[dict[str, Any]] = []
        for i, chunk in enumerate(self.chunks):
            if normalized_doc_id and chunk.doc_id.lower() != normalized_doc_id:
                continue
            if normalized_doc_filter and normalized_doc_filter not in chunk.doc_id.lower():
                continue
            chunk_terms = set(_normalize_terms(chunk.text))
            matched_terms = sorted(query_terms.intersection(chunk_terms))
            overlap = len(matched_terms)
            keyword_score = overlap / max(len(query_terms), 1)
            semantic_score = (
                float(semantic_scores[i]) if semantic_scores is not None else 0.0
            )

            hybrid_score = (
                self.retrieval_config.lexical_weight * float(lexical_scores[i])
                + self.retrieval_config.keyword_weight * keyword_score
                + self.retrieval_config.semantic_weight * semantic_score
            )
            rerank_bonus = self._rerank_bonus(query_terms, chunk_terms)
            final_score = (
                hybrid_score + self.retrieval_config.rerank_boost * rerank_bonus
            )

            if final_score >= max(min_score, 0.0):
                ranked.append(
                    {
                        "chunk": chunk,
                        "score": final_score,
                        "lexical_score": float(lexical_scores[i]),
                        "keyword_score": keyword_score,
                        "semantic_score": semantic_score,
                        "matched_terms": matched_terms,
                    }
                )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

    def answer_with_citations(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
        doc_id: str | None = None,
        doc_id_contains: str | None = None,
    ) -> AnswerResult:
        hits = self.retrieve(
            query,
            top_k=top_k,
            min_score=min_score,
            doc_id=doc_id,
            doc_id_contains=doc_id_contains,
        )
        if not hits:
            return AnswerResult(
                answer="Não encontrei contexto relevante para responder.", citations=[]
            )

        best = hits[0]["chunk"].text
        summary = best[:320] + ("..." if len(best) > 320 else "")
        citations = [
            Citation(
                doc_id=h["chunk"].doc_id,
                chunk_start=h["chunk"].start,
                chunk_end=h["chunk"].end,
                score=round(float(h["score"]), 4),
                excerpt=h["chunk"].text[:180],
            )
            for h in hits
        ]

        refs = " ".join(f"[{i + 1}]" for i in range(len(citations)))
        answer = (
            "Resposta baseada no contexto recuperado:\n"
            f"{summary}\n\n"
            f"Referências: {refs}"
        )
        return AnswerResult(answer=answer, citations=citations)

    def answer(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
        doc_id: str | None = None,
        doc_id_contains: str | None = None,
    ) -> str:
        return self.answer_with_citations(
            query,
            top_k=top_k,
            min_score=min_score,
            doc_id=doc_id,
            doc_id_contains=doc_id_contains,
        ).answer

    def evaluate_precision_at_k(
        self, dataset_path: str | Path, k: int = 3
    ) -> dict[str, Any]:
        if k < 1:
            raise ValueError("k must be >= 1")
        entries = _load_eval_jsonl(Path(dataset_path))
        if not entries:
            raise ValueError("evaluation dataset is empty")

        scores: list[float] = []
        details: list[dict[str, Any]] = []

        for item in entries:
            query = item["query"]
            relevant_doc_ids = set(item["relevant_doc_ids"])
            hits = self.retrieve(query, top_k=k)
            predicted = [h["chunk"].doc_id for h in hits]
            correct = sum(1 for doc_id in predicted if doc_id in relevant_doc_ids)
            precision = correct / max(k, 1)
            scores.append(precision)
            details.append({"query": query, "precision": precision, "hits": predicted})

        return {
            "metric": f"precision@{k}",
            "value": sum(scores) / len(scores),
            "samples": len(scores),
            "details": details,
        }

    def save(self, path: str | Path) -> None:
        payload = {
            "index_version": self.INDEX_VERSION,
            "vectorizer": self.vectorizer,
            "chunks": self.chunks,
            "matrix": self._matrix,
            "ingest_config": self.ingest_config.__dict__,
            "retrieval_config": self.retrieval_config.__dict__,
            "doc_hashes": self._doc_hashes,
            "semantic_embeddings": self._semantic_embeddings,
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as f:
            pickle.dump(payload, f)
        logger.info(
            "index_saved", extra={"path": str(path), "chunks": len(self.chunks)}
        )

    @classmethod
    def load(cls, path: str | Path) -> "RAGPipeline":
        with Path(path).open("rb") as f:
            payload = pickle.load(f)

        if payload.get("index_version") != cls.INDEX_VERSION:
            raise ValueError("index version mismatch")

        instance = cls(
            ingest_config=IngestConfig(**payload.get("ingest_config", {})),
            retrieval_config=RetrievalConfig(**payload.get("retrieval_config", {})),
        )
        instance.vectorizer = payload["vectorizer"]
        instance.chunks = payload["chunks"]
        instance._matrix = payload["matrix"]
        instance._doc_hashes = payload.get("doc_hashes", {})
        instance._semantic_embeddings = payload.get("semantic_embeddings")
        return instance

    def _encode_semantic_texts(self, texts: list[str]) -> Any:
        if not self.retrieval_config.use_semantic or not texts:
            return None
        try:
            if self._semantic_model is None:
                from sentence_transformers import SentenceTransformer

                self._semantic_model = SentenceTransformer(
                    self.retrieval_config.semantic_model
                )
            return self._semantic_model.encode(texts)
        except Exception:
            logger.warning("semantic_embeddings_disabled", exc_info=True)
            self.retrieval_config.use_semantic = False
            return None

    def _semantic_similarity(self, query: str) -> Any:
        if (
            not self.retrieval_config.use_semantic
            or self._semantic_embeddings is None
            or not query.strip()
        ):
            return None
        try:
            if self._semantic_model is None:
                from sentence_transformers import SentenceTransformer

                self._semantic_model = SentenceTransformer(
                    self.retrieval_config.semantic_model
                )
            query_embedding = self._semantic_model.encode([query])
            return cosine_similarity(query_embedding, self._semantic_embeddings)[0]
        except Exception:
            logger.warning("semantic_similarity_failed", exc_info=True)
            return None

    def _read_and_chunk(self, path: Path, seen_hashes: set[str]) -> list[Chunk]:
        self._validate_file(path)
        text = path.read_text(encoding="utf-8", errors="ignore")

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen_hashes:
            logger.info("duplicate_document_skipped", extra={"path": str(path)})
            return []

        if len(text.strip()) < self.ingest_config.min_chars:
            logger.info("document_too_short_skipped", extra={"path": str(path)})
            return []

        seen_hashes.add(digest)
        self._doc_hashes[str(path)] = digest

        return chunk_text(
            text,
            doc_id=str(path),
            chunk_size=self.ingest_config.chunk_size,
            overlap=self.ingest_config.overlap,
            strategy=self.ingest_config.chunk_strategy,
        )

    def _validate_file(self, path: Path) -> None:
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"unsupported extension: {path.suffix}")
        if not path.exists() or not path.is_file():
            raise ValueError(f"invalid file: {path}")
        max_bytes = self.ingest_config.max_file_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise ValueError(f"file too large: {path}")

    @staticmethod
    def _rerank_bonus(query_terms: set[str], chunk_terms: set[str]) -> float:
        if not query_terms:
            return 0.0
        coverage = len(query_terms.intersection(chunk_terms)) / len(query_terms)
        rare_term_bonus = (
            1.0 if len(query_terms.intersection(chunk_terms)) >= 2 else 0.0
        )
        return 0.7 * coverage + 0.3 * rare_term_bonus


def _normalize_terms(text: str) -> list[str]:
    return [
        token.strip(".,:;!?()[]{}\"'").lower()
        for token in text.split()
        if token.strip()
    ]


def citations_to_dict(citations: list[Citation]) -> list[dict[str, Any]]:
    return [asdict(c) for c in citations]


def _load_eval_jsonl(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "query" not in obj or "relevant_doc_ids" not in obj:
                raise ValueError(
                    "invalid evaluation row: require query and relevant_doc_ids"
                )
            entries.append(obj)
    return entries
