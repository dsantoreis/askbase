from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .evaluation import evaluate_context_precision
from .observability import configure_logging, instrumented_call_next, metrics_endpoint
from .pipeline import RAGPipeline, citations_to_dict
from .security import AuthContext, AuthManager, InMemoryRateLimiter


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


class IngestRequest(BaseModel):
    paths: list[str]


class EvalRequest(BaseModel):
    dataset_path: str
    k: int = Field(default=3, ge=1, le=10)


def create_app(index_path: str = "artifacts/rag_index.pkl") -> FastAPI:
    configure_logging()
    app = FastAPI(title="RAG Enterprise Platform", version="4.0.0")
    state = {
        "index_path": Path(index_path),
        "rag": None,
        "auth": AuthManager(),
        "limiter": InMemoryRateLimiter(),
    }

    if state["index_path"].exists():
        state["rag"] = RAGPipeline.load(state["index_path"])

    async def add_metrics(request: Request, call_next):
        return await instrumented_call_next(request, call_next)

    app.middleware("http")(add_metrics)

    def auth_dep(request: Request) -> AuthContext:
        key = request.client.host if request.client else "unknown"
        limit, remaining = state["limiter"].check(key)
        request.state.rate_limit = {"limit": limit, "remaining": remaining}
        return state["auth"].authenticate(request)

    @app.api_route("/health", methods=["GET", "HEAD"])
    def health() -> dict:
        return {"status": "ok", "index_loaded": state["rag"] is not None}

    @app.api_route("/readyz", methods=["GET", "HEAD"])
    def readyz() -> dict:
        chunks_loaded = len(state["rag"].chunks) if state["rag"] else 0
        return {
            "ready": state["rag"] is not None,
            "chunks_loaded": chunks_loaded,
            "index_path": str(state["index_path"]),
        }

    @app.get("/metrics")
    async def metrics() -> object:
        return await metrics_endpoint()

    @app.get("/admin/stats")
    def admin_stats(ctx: AuthContext = Depends(auth_dep)) -> dict:
        AuthManager.require_role(ctx, "admin")
        return {
            "chunks_loaded": len(state["rag"].chunks) if state["rag"] else 0,
            "index_path": str(state["index_path"]),
        }

    @app.post("/ingest")
    def ingest(req: IngestRequest, ctx: AuthContext = Depends(auth_dep)) -> dict:
        AuthManager.require_role(ctx, "admin")
        rag = RAGPipeline()
        chunk_count = rag.ingest(req.paths)
        rag.save(state["index_path"])
        state["rag"] = rag
        return {"chunks_indexed": chunk_count, "index_path": str(state["index_path"])}

    @app.post("/ask")
    def ask(req: AskRequest, request: Request, _: AuthContext = Depends(auth_dep)) -> dict:
        if state["rag"] is None:
            raise HTTPException(status_code=400, detail="index not loaded")
        result = state["rag"].ask(req.query, top_k=req.top_k)
        return {
            "answer": result.text,
            "citations": citations_to_dict(result.citations),
            "citations_count": len(result.citations),
            "rate_limit": request.state.rate_limit,
        }

    @app.post("/evaluate")
    def evaluate(req: EvalRequest, ctx: AuthContext = Depends(auth_dep)) -> dict:
        AuthManager.require_role(ctx, "admin")
        if not state["index_path"].exists():
            raise HTTPException(status_code=400, detail="index not found")
        return evaluate_context_precision(state["index_path"], req.dataset_path, k=req.k)

    return app
