from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .evaluation import evaluate_context_precision
from .pipeline import RAGPipeline, citations_to_dict


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class IngestRequest(BaseModel):
    paths: list[str]


class EvalRequest(BaseModel):
    dataset_path: str
    k: int = Field(default=3, ge=1, le=10)


def create_app(index_path: str = "artifacts/rag_index.pkl") -> FastAPI:
    app = FastAPI(title="RAG Pipeline Demo", version="3.0.0")
    state = {"index_path": Path(index_path), "rag": None}

    if state["index_path"].exists():
        state["rag"] = RAGPipeline.load(state["index_path"])

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "index_loaded": state["rag"] is not None}

    @app.post("/ingest")
    def ingest(req: IngestRequest) -> dict:
        rag = RAGPipeline()
        chunk_count = rag.ingest(req.paths)
        rag.save(state["index_path"])
        state["rag"] = rag
        return {"chunks_indexed": chunk_count, "index_path": str(state["index_path"])}

    @app.post("/ask")
    def ask(req: AskRequest) -> dict:
        if state["rag"] is None:
            raise HTTPException(status_code=400, detail="index not loaded")
        result = state["rag"].ask(req.query, top_k=req.top_k)
        return {
            "answer": result.text,
            "citations": citations_to_dict(result.citations),
            "citations_count": len(result.citations),
        }

    @app.post("/evaluate")
    def evaluate(req: EvalRequest) -> dict:
        if not state["index_path"].exists():
            raise HTTPException(status_code=400, detail="index not found")
        return evaluate_context_precision(state["index_path"], req.dataset_path, k=req.k)

    return app
