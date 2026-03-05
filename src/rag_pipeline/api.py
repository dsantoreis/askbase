from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from .pipeline import RAGPipeline, citations_to_dict


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    citations: list[dict]


def _render_metrics(state: dict) -> str:
    uptime_seconds = time.monotonic() - state["started_at"]
    index_loaded = 1 if state["rag"] is not None else 0

    lines = [
        "# HELP rag_api_uptime_seconds Process uptime in seconds.",
        "# TYPE rag_api_uptime_seconds gauge",
        f"rag_api_uptime_seconds {uptime_seconds:.6f}",
        "# HELP rag_api_index_loaded Whether an index is loaded (1=yes, 0=no).",
        "# TYPE rag_api_index_loaded gauge",
        f"rag_api_index_loaded {index_loaded}",
        "# HELP rag_api_health_requests_total Total number of /health requests.",
        "# TYPE rag_api_health_requests_total counter",
        f"rag_api_health_requests_total {state['health_requests_total']}",
        "# HELP rag_api_ask_requests_total Total number of /ask requests.",
        "# TYPE rag_api_ask_requests_total counter",
        f"rag_api_ask_requests_total {state['ask_requests_total']}",
        "# HELP rag_api_ask_errors_total Total number of /ask requests failed.",
        "# TYPE rag_api_ask_errors_total counter",
        f"rag_api_ask_errors_total {state['ask_errors_total']}",
    ]

    if state["ask_latency_seconds"]:
        avg_latency = sum(state["ask_latency_seconds"]) / len(
            state["ask_latency_seconds"]
        )
    else:
        avg_latency = 0.0

    lines.extend(
        [
            "# HELP rag_api_ask_latency_avg_seconds Average latency of /ask in seconds.",
            "# TYPE rag_api_ask_latency_avg_seconds gauge",
            f"rag_api_ask_latency_avg_seconds {avg_latency:.6f}",
        ]
    )

    return "\n".join(lines) + "\n"


def create_app(index_path: str = "rag_index.pkl") -> FastAPI:
    app = FastAPI(title="RAG Pipeline Demo API", version="1.2.0")
    index = Path(index_path)
    state = {
        "index_path": index,
        "rag": RAGPipeline.load(index) if index.exists() else None,
        "started_at": time.monotonic(),
        "health_requests_total": 0,
        "ask_requests_total": 0,
        "ask_errors_total": 0,
        "ask_latency_seconds": [],
    }

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        state["health_requests_total"] += 1
        return {
            "status": "ok",
            "index_loaded": state["rag"] is not None,
            "index_path": str(state["index_path"]),
        }

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(
            content=_render_metrics(state),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        state["ask_requests_total"] += 1
        started = time.perf_counter()
        rag = state["rag"]
        if rag is None:
            state["ask_errors_total"] += 1
            raise HTTPException(
                status_code=400, detail="index not loaded; run ingest first"
            )
        result = rag.answer_with_citations(req.query, top_k=req.top_k)
        state["ask_latency_seconds"].append(time.perf_counter() - started)
        return AskResponse(
            answer=result.answer, citations=citations_to_dict(result.citations)
        )

    return app
