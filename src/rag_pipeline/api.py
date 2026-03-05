from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .chunking import chunk_text
from .pipeline import RAGPipeline, citations_to_dict


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    citations: list[dict]


class IngestRequest(BaseModel):
    text: str = Field(min_length=1)
    doc_id: str = Field(default="api:document", min_length=1)


class IngestResponse(BaseModel):
    chunks_indexed: int
    index_path: str


class VersionResponse(BaseModel):
    app_version: str
    index_path: str


class ReadyResponse(BaseModel):
    status: str
    index_loaded: bool
    index_exists: bool
    index_readable: bool
    artifacts_dir_exists: bool
    artifacts_dir_writable: bool
    index_path: str
    artifacts_dir: str


class DiagResponse(BaseModel):
    status: str
    index_loaded: bool
    index_path: str
    index_file: dict
    index_snapshot: dict
    artifacts_snapshot: dict


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
        "# HELP rag_api_ingest_requests_total Total number of /ingest requests.",
        "# TYPE rag_api_ingest_requests_total counter",
        f"rag_api_ingest_requests_total {state['ingest_requests_total']}",
        "# HELP rag_api_ingest_errors_total Total number of /ingest requests failed.",
        "# TYPE rag_api_ingest_errors_total counter",
        f"rag_api_ingest_errors_total {state['ingest_errors_total']}",
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
        "ingest_requests_total": 0,
        "ingest_errors_total": 0,
    }

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        state["health_requests_total"] += 1
        return {
            "status": "ok",
            "index_loaded": state["rag"] is not None,
            "index_path": str(state["index_path"]),
        }

    @app.get("/readyz", response_model=ReadyResponse)
    def readyz() -> JSONResponse:
        index_path = state["index_path"]
        artifacts_dir = index_path.parent

        index_loaded = state["rag"] is not None
        index_exists = index_path.exists()
        index_readable = (
            index_exists and index_path.is_file() and os.access(index_path, os.R_OK)
        )
        artifacts_dir_exists = artifacts_dir.exists() and artifacts_dir.is_dir()
        artifacts_dir_writable = artifacts_dir_exists and os.access(
            artifacts_dir, os.W_OK | os.X_OK
        )

        ready = (
            index_loaded
            and index_exists
            and index_readable
            and artifacts_dir_exists
            and bool(artifacts_dir_writable)
        )
        payload = ReadyResponse(
            status="ready" if ready else "not_ready",
            index_loaded=index_loaded,
            index_exists=index_exists,
            index_readable=index_readable,
            artifacts_dir_exists=artifacts_dir_exists,
            artifacts_dir_writable=bool(artifacts_dir_writable),
            index_path=str(index_path),
            artifacts_dir=str(artifacts_dir),
        )

        return JSONResponse(
            status_code=200 if ready else 503,
            content=payload.model_dump(),
        )

    @app.get("/version", response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse(
            app_version=app.version,
            index_path=str(state["index_path"]),
        )

    @app.get("/diag", response_model=DiagResponse)
    def diag() -> DiagResponse:
        index_path = state["index_path"]
        artifacts_dir = index_path.parent
        rag = state["rag"]

        index_exists = index_path.exists() and index_path.is_file()
        index_mtime = (
            datetime.fromtimestamp(index_path.stat().st_mtime, tz=UTC).isoformat()
            if index_exists
            else None
        )
        index_file = {
            "exists": index_exists,
            "readable": index_exists and os.access(index_path, os.R_OK),
            "size_bytes": index_path.stat().st_size if index_exists else 0,
            "modified_at": index_mtime,
        }

        if rag is None:
            index_snapshot = {
                "index_version": None,
                "chunks_count": 0,
                "unique_doc_ids_count": 0,
                "vectorizer_vocab_size": 0,
            }
        else:
            index_snapshot = {
                "index_version": getattr(rag, "INDEX_VERSION", None),
                "chunks_count": len(rag.chunks),
                "unique_doc_ids_count": len({c.doc_id for c in rag.chunks}),
                "vectorizer_vocab_size": len(
                    getattr(rag.vectorizer, "vocabulary_", {})
                ),
            }

        extension_counts: dict[str, int] = {}
        files_count = 0
        total_size_bytes = 0
        if artifacts_dir.exists() and artifacts_dir.is_dir():
            for item in artifacts_dir.iterdir():
                if not item.is_file():
                    continue
                files_count += 1
                total_size_bytes += item.stat().st_size
                ext = item.suffix.lower() or "<no_ext>"
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

        artifacts_snapshot = {
            "dir_exists": artifacts_dir.exists() and artifacts_dir.is_dir(),
            "dir_readable": artifacts_dir.exists()
            and os.access(artifacts_dir, os.R_OK | os.X_OK),
            "dir_writable": artifacts_dir.exists()
            and os.access(artifacts_dir, os.W_OK | os.X_OK),
            "files_count": files_count,
            "total_size_bytes": total_size_bytes,
            "files_by_extension": extension_counts,
        }

        return DiagResponse(
            status="ok",
            index_loaded=rag is not None,
            index_path=str(index_path),
            index_file=index_file,
            index_snapshot=index_snapshot,
            artifacts_snapshot=artifacts_snapshot,
        )

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(
            content=_render_metrics(state),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.post("/ingest", response_model=IngestResponse)
    def ingest(req: IngestRequest) -> IngestResponse:
        state["ingest_requests_total"] += 1

        rag = state["rag"]
        if rag is None:
            rag = RAGPipeline()
            state["rag"] = rag

        text = req.text.strip()
        if len(text) < rag.ingest_config.min_chars:
            state["ingest_errors_total"] += 1
            raise HTTPException(
                status_code=400,
                detail=(f"document too short; min_chars={rag.ingest_config.min_chars}"),
            )

        chunks = chunk_text(
            text,
            doc_id=req.doc_id,
            chunk_size=rag.ingest_config.chunk_size,
            overlap=rag.ingest_config.overlap,
            strategy=rag.ingest_config.chunk_strategy,
        )
        if not chunks:
            state["ingest_errors_total"] += 1
            raise HTTPException(status_code=400, detail="document has no valid content")

        rag.chunks = [c for c in rag.chunks if c.doc_id != req.doc_id] + chunks
        texts = [c.text for c in rag.chunks]
        rag._matrix = rag.vectorizer.fit_transform(texts) if texts else None
        rag.save(state["index_path"])

        return IngestResponse(
            chunks_indexed=len(chunks), index_path=str(state["index_path"])
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
