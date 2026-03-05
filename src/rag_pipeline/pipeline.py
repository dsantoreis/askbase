from pathlib import Path
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunking import Chunk, chunk_text


class RAGPipeline:
    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.chunks: list[Chunk] = []
        self._matrix = None

    def ingest_paths(self, paths, chunk_size: int = 500, overlap: int = 100) -> int:
        all_chunks: list[Chunk] = []
        for path in paths:
            p = Path(path)
            if p.is_dir():
                for file in sorted(p.rglob("*")):
                    if file.is_file() and file.suffix.lower() in {".txt", ".md"}:
                        all_chunks.extend(self._read_and_chunk(file, chunk_size, overlap))
            elif p.is_file():
                all_chunks.extend(self._read_and_chunk(p, chunk_size, overlap))

        self.chunks = all_chunks
        texts = [c.text for c in self.chunks]
        self._matrix = self.vectorizer.fit_transform(texts) if texts else None
        return len(self.chunks)

    def retrieve(self, query: str, top_k: int = 3):
        if not query.strip() or self._matrix is None or not self.chunks:
            return []

        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self._matrix)[0]
        ranked_idx = sims.argsort()[::-1][:top_k]
        out = []
        for i in ranked_idx:
            if sims[i] > 0:
                out.append({"chunk": self.chunks[i], "score": float(sims[i])})
        return out

    def answer(self, query: str, top_k: int = 3) -> str:
        hits = self.retrieve(query, top_k=top_k)
        if not hits:
            return "Não encontrei contexto relevante para responder."

        context_lines = [f"[{i+1}] ({h['chunk'].doc_id}) {h['chunk'].text}" for i, h in enumerate(hits)]
        best = hits[0]["chunk"].text
        summary = best[:280] + ("..." if len(best) > 280 else "")
        return "Resposta baseada no contexto recuperado:\n" + summary + "\n\nContexto usado:\n" + "\n".join(context_lines)

    def save(self, path) -> None:
        payload = {"vectorizer": self.vectorizer, "chunks": self.chunks, "matrix": self._matrix}
        with Path(path).open("wb") as f:
            pickle.dump(payload, f)

    @classmethod
    def load(cls, path):
        with Path(path).open("rb") as f:
            payload = pickle.load(f)
        instance = cls()
        instance.vectorizer = payload["vectorizer"]
        instance.chunks = payload["chunks"]
        instance._matrix = payload["matrix"]
        return instance

    def _read_and_chunk(self, path: Path, chunk_size: int, overlap: int) -> list[Chunk]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return chunk_text(text, doc_id=str(path), chunk_size=chunk_size, overlap=overlap)
