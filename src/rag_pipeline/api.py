from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .pipeline import RAGPipeline


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str



def create_app(index_path: str = "rag_index.pkl") -> FastAPI:
    app = FastAPI(title="RAG Pipeline Demo API", version="1.0.0")
    index = Path(index_path)
    state = {"index_path": index, "rag": RAGPipeline.load(index) if index.exists() else None}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        rag = state["rag"]
        if rag is None:
            raise HTTPException(status_code=400, detail="index not loaded; run ingest first")
        return AskResponse(answer=rag.answer(req.query, top_k=req.top_k))

    return app
