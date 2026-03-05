from __future__ import annotations

import hashlib
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, field_validator, model_validator

from .chunking import chunk_text
from .pipeline import RAGPipeline, citations_to_dict

LATENCY_HISTORY_LIMIT = 1000
ASK_QUERY_MAX_CHARS = 2000
ASK_TOP_K_MAX = 20
DOC_ID_MAX_CHARS = 256
INGEST_TEXT_MAX_CHARS = 200_000


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=ASK_QUERY_MAX_CHARS)
    top_k: int = Field(default=3, ge=1, le=ASK_TOP_K_MAX)
    min_score: float = Field(default=0.0, ge=0.0)
    doc_id: str | None = Field(default=None, min_length=1, max_length=DOC_ID_MAX_CHARS)
    doc_id_contains: str | None = Field(
        default=None, min_length=1, max_length=DOC_ID_MAX_CHARS
    )

    @model_validator(mode="after")
    def validate_doc_filters_are_mutually_exclusive(self) -> "AskRequest":
        if self.doc_id is not None and self.doc_id_contains is not None:
            raise ValueError("use either doc_id or doc_id_contains, not both")
        return self

    @field_validator("query")
    @classmethod
    def validate_query_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("doc_id must not be blank")
        return normalized

    @field_validator("min_score")
    @classmethod
    def validate_min_score_is_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("min_score must be finite")
        return value

    @field_validator("doc_id_contains")
    @classmethod
    def validate_doc_id_contains_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("doc_id_contains must not be blank")
        return normalized


class AskResponse(BaseModel):
    answer: str
    citations: list[dict]
    citations_count: int = Field(ge=0)


class IngestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=INGEST_TEXT_MAX_CHARS)
    doc_id: str = Field(
        default="api:document", min_length=1, max_length=DOC_ID_MAX_CHARS
    )
    replace_existing: bool = True

    @field_validator("text")
    @classmethod
    def validate_text_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be blank")
        return normalized

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("doc_id must not be blank")
        return normalized


class IngestResponse(BaseModel):
    chunks_indexed: int
    index_path: str


class VersionResponse(BaseModel):
    app_version: str
    index_path: str


class BuildInfoResponse(BaseModel):
    app_version: str
    index_path: str
    started_at: str


class BuildLiteResponse(BaseModel):
    app_version: str
    started_at: str


class ReadyResponse(BaseModel):
    status: str
    index_loaded: bool
    index_exists: bool
    index_readable: bool
    artifacts_dir_exists: bool
    artifacts_dir_writable: bool
    index_path: str
    artifacts_dir: str


class StatuszResponse(BaseModel):
    ready: bool
    uptime_seconds: float
    app_version: str


class PingzResponse(BaseModel):
    status: str
    latency_ms: float
    timestamp_utc: str


class TimezResponse(BaseModel):
    server_time_utc: str
    uptime_seconds: float


class HealthzLiteResponse(BaseModel):
    status: str
    uptime_seconds: float


class AlivezResponse(BaseModel):
    status: str


class EchozResponse(BaseModel):
    status: str
    service: str


class ReadyzLiteResponse(BaseModel):
    ready: bool
    uptime_seconds: float


class ReadyzReasonResponse(BaseModel):
    ready: bool
    reasons: list[str]
    index_path: str


class MetaLiteResponse(BaseModel):
    app_name: str
    app_version: str
    uptime_seconds: float


class DiagResponse(BaseModel):
    status: str
    index_loaded: bool
    index_path: str
    index_file: dict
    index_snapshot: dict
    artifacts_snapshot: dict


class DiagLiteResponse(BaseModel):
    status: str
    index_loaded: bool
    index_snapshot: dict


class StatsResponse(BaseModel):
    status: str
    uptime_seconds: float
    requests_total: int
    ask_latency_avg_seconds: float
    ask_latency_samples: int
    ingest_latency_avg_seconds: float
    ingest_latency_samples: int
    counters: dict[str, int]


class OpenApiLiteRoute(BaseModel):
    path: str
    methods: list[str]


class OpenApiLiteResponse(BaseModel):
    status: str
    app_version: str
    routes: list[OpenApiLiteRoute]


class RoutesHashResponse(BaseModel):
    status: str
    algorithm: str
    routes_hash: str
    routes_count: int


class LimitsResponse(BaseModel):
    ask_query_max_chars: int
    ask_top_k_max: int
    doc_id_max_chars: int
    ingest_text_max_chars: int


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
        "# HELP rag_api_healthz_lite_requests_total Total number of /healthz-lite requests.",
        "# TYPE rag_api_healthz_lite_requests_total counter",
        f"rag_api_healthz_lite_requests_total {state['healthz_lite_requests_total']}",
        "# HELP rag_api_alivez_requests_total Total number of /alivez requests.",
        "# TYPE rag_api_alivez_requests_total counter",
        f"rag_api_alivez_requests_total {state['alivez_requests_total']}",
        "# HELP rag_api_echoz_requests_total Total number of /echoz requests.",
        "# TYPE rag_api_echoz_requests_total counter",
        f"rag_api_echoz_requests_total {state['echoz_requests_total']}",
        "# HELP rag_api_pingz_requests_total Total number of /pingz requests.",
        "# TYPE rag_api_pingz_requests_total counter",
        f"rag_api_pingz_requests_total {state['pingz_requests_total']}",
        "# HELP rag_api_timez_requests_total Total number of /timez requests.",
        "# TYPE rag_api_timez_requests_total counter",
        f"rag_api_timez_requests_total {state['timez_requests_total']}",
        "# HELP rag_api_readyz_requests_total Total number of /readyz requests.",
        "# TYPE rag_api_readyz_requests_total counter",
        f"rag_api_readyz_requests_total {state['ready_requests_total']}",
        "# HELP rag_api_readyz_lite_requests_total Total number of /readyz-lite requests.",
        "# TYPE rag_api_readyz_lite_requests_total counter",
        f"rag_api_readyz_lite_requests_total {state['readyz_lite_requests_total']}",
        "# HELP rag_api_readyz_reason_requests_total Total number of /readyz-reason requests.",
        "# TYPE rag_api_readyz_reason_requests_total counter",
        f"rag_api_readyz_reason_requests_total {state['readyz_reason_requests_total']}",
        "# HELP rag_api_statusz_requests_total Total number of /statusz requests.",
        "# TYPE rag_api_statusz_requests_total counter",
        f"rag_api_statusz_requests_total {state['statusz_requests_total']}",
        "# HELP rag_api_meta_lite_requests_total Total number of /meta-lite requests.",
        "# TYPE rag_api_meta_lite_requests_total counter",
        f"rag_api_meta_lite_requests_total {state['meta_lite_requests_total']}",
        "# HELP rag_api_ask_requests_total Total number of /ask requests.",
        "# TYPE rag_api_ask_requests_total counter",
        f"rag_api_ask_requests_total {state['ask_requests_total']}",
        "# HELP rag_api_ask_errors_total Total number of /ask requests failed.",
        "# TYPE rag_api_ask_errors_total counter",
        f"rag_api_ask_errors_total {state['ask_errors_total']}",
        "# HELP rag_api_ask_safe_requests_total Total number of /ask-safe requests.",
        "# TYPE rag_api_ask_safe_requests_total counter",
        f"rag_api_ask_safe_requests_total {state['ask_safe_requests_total']}",
        "# HELP rag_api_ask_safe_errors_total Total number of /ask-safe requests failed.",
        "# TYPE rag_api_ask_safe_errors_total counter",
        f"rag_api_ask_safe_errors_total {state['ask_safe_errors_total']}",
        "# HELP rag_api_ingest_requests_total Total number of /ingest requests.",
        "# TYPE rag_api_ingest_requests_total counter",
        f"rag_api_ingest_requests_total {state['ingest_requests_total']}",
        "# HELP rag_api_ingest_errors_total Total number of /ingest requests failed.",
        "# TYPE rag_api_ingest_errors_total counter",
        f"rag_api_ingest_errors_total {state['ingest_errors_total']}",
        "# HELP rag_api_version_requests_total Total number of /version requests.",
        "# TYPE rag_api_version_requests_total counter",
        f"rag_api_version_requests_total {state['version_requests_total']}",
        "# HELP rag_api_build_info_requests_total Total number of /build-info requests.",
        "# TYPE rag_api_build_info_requests_total counter",
        f"rag_api_build_info_requests_total {state['build_info_requests_total']}",
        "# HELP rag_api_build_lite_requests_total Total number of /build-lite requests.",
        "# TYPE rag_api_build_lite_requests_total counter",
        f"rag_api_build_lite_requests_total {state['build_lite_requests_total']}",
        "# HELP rag_api_metrics_requests_total Total number of /metrics requests.",
        "# TYPE rag_api_metrics_requests_total counter",
        f"rag_api_metrics_requests_total {state['metrics_requests_total']}",
        "# HELP rag_api_stats_requests_total Total number of /stats requests.",
        "# TYPE rag_api_stats_requests_total counter",
        f"rag_api_stats_requests_total {state['stats_requests_total']}",
        "# HELP rag_api_limits_requests_total Total number of /limits requests.",
        "# TYPE rag_api_limits_requests_total counter",
        f"rag_api_limits_requests_total {state['limits_requests_total']}",
        "# HELP rag_api_diag_requests_total Total number of /diag requests.",
        "# TYPE rag_api_diag_requests_total counter",
        f"rag_api_diag_requests_total {state['diag_requests_total']}",
        "# HELP rag_api_diag_lite_requests_total Total number of /diag-lite requests.",
        "# TYPE rag_api_diag_lite_requests_total counter",
        f"rag_api_diag_lite_requests_total {state['diag_lite_requests_total']}",
        "# HELP rag_api_openapi_lite_requests_total Total number of /openapi-lite requests.",
        "# TYPE rag_api_openapi_lite_requests_total counter",
        f"rag_api_openapi_lite_requests_total {state['openapi_lite_requests_total']}",
        "# HELP rag_api_routes_hash_requests_total Total number of /routes-hash requests.",
        "# TYPE rag_api_routes_hash_requests_total counter",
        f"rag_api_routes_hash_requests_total {state['routes_hash_requests_total']}",
    ]

    if state["ask_latency_seconds"]:
        ask_avg_latency = sum(state["ask_latency_seconds"]) / len(
            state["ask_latency_seconds"]
        )
    else:
        ask_avg_latency = 0.0

    if state["ingest_latency_seconds"]:
        ingest_avg_latency = sum(state["ingest_latency_seconds"]) / len(
            state["ingest_latency_seconds"]
        )
    else:
        ingest_avg_latency = 0.0

    lines.extend(
        [
            "# HELP rag_api_ask_latency_avg_seconds Average latency of /ask in seconds.",
            "# TYPE rag_api_ask_latency_avg_seconds gauge",
            f"rag_api_ask_latency_avg_seconds {ask_avg_latency:.6f}",
            "# HELP rag_api_ingest_latency_avg_seconds Average latency of /ingest in seconds.",
            "# TYPE rag_api_ingest_latency_avg_seconds gauge",
            f"rag_api_ingest_latency_avg_seconds {ingest_avg_latency:.6f}",
        ]
    )

    return "\n".join(lines) + "\n"


def _safe_route_summary(app: FastAPI) -> list[OpenApiLiteRoute]:
    routes: list[OpenApiLiteRoute] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.include_in_schema:
            continue
        methods = sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"})
        routes.append(OpenApiLiteRoute(path=route.path, methods=methods))

    return sorted(routes, key=lambda item: item.path)


def _stable_routes_hash(routes: list[OpenApiLiteRoute]) -> str:
    canonical_routes = [
        {"path": route.path, "methods": sorted(route.methods)} for route in routes
    ]
    payload = json.dumps(
        canonical_routes,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _record_latency(samples: list[float], value: float) -> None:
    samples.append(value)
    overflow = len(samples) - LATENCY_HISTORY_LIMIT
    if overflow > 0:
        del samples[:overflow]


def create_app(index_path: str = "rag_index.pkl") -> FastAPI:
    app = FastAPI(title="RAG Pipeline Demo API", version="1.2.0")
    index = Path(index_path)
    state = {
        "index_path": index,
        "rag": RAGPipeline.load(index) if index.exists() else None,
        "started_at": time.monotonic(),
        "started_at_iso": datetime.now(tz=UTC).isoformat(),
        "health_requests_total": 0,
        "healthz_lite_requests_total": 0,
        "alivez_requests_total": 0,
        "echoz_requests_total": 0,
        "ready_requests_total": 0,
        "readyz_lite_requests_total": 0,
        "readyz_reason_requests_total": 0,
        "statusz_requests_total": 0,
        "meta_lite_requests_total": 0,
        "pingz_requests_total": 0,
        "timez_requests_total": 0,
        "diag_requests_total": 0,
        "diag_lite_requests_total": 0,
        "openapi_lite_requests_total": 0,
        "routes_hash_requests_total": 0,
        "version_requests_total": 0,
        "build_info_requests_total": 0,
        "build_lite_requests_total": 0,
        "metrics_requests_total": 0,
        "stats_requests_total": 0,
        "limits_requests_total": 0,
        "ask_requests_total": 0,
        "ask_errors_total": 0,
        "ask_safe_requests_total": 0,
        "ask_safe_errors_total": 0,
        "ask_latency_seconds": [],
        "ingest_latency_seconds": [],
        "ingest_requests_total": 0,
        "ingest_errors_total": 0,
    }

    def _is_ready() -> bool:
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
        return bool(
            index_loaded
            and index_exists
            and index_readable
            and artifacts_dir_exists
            and artifacts_dir_writable
        )

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        state["health_requests_total"] += 1
        return {
            "status": "ok",
            "index_loaded": state["rag"] is not None,
            "index_path": str(state["index_path"]),
        }

    @app.get("/healthz-lite", response_model=HealthzLiteResponse)
    def healthz_lite() -> HealthzLiteResponse:
        state["healthz_lite_requests_total"] += 1
        return HealthzLiteResponse(
            status="ok",
            uptime_seconds=time.monotonic() - state["started_at"],
        )

    @app.get("/alivez", response_model=AlivezResponse)
    def alivez() -> AlivezResponse:
        state["alivez_requests_total"] += 1
        return AlivezResponse(status="alive")

    @app.get("/echoz", response_model=EchozResponse)
    def echoz() -> EchozResponse:
        state["echoz_requests_total"] += 1
        return EchozResponse(status="ok", service=app.title)

    @app.get("/pingz", response_model=PingzResponse)
    def pingz() -> PingzResponse:
        started = time.perf_counter()
        state["pingz_requests_total"] += 1
        latency_ms = (time.perf_counter() - started) * 1000
        return PingzResponse(
            status="ok",
            latency_ms=latency_ms,
            timestamp_utc=datetime.now(tz=UTC).isoformat(),
        )

    @app.get("/timez", response_model=TimezResponse)
    def timez() -> TimezResponse:
        state["timez_requests_total"] += 1
        return TimezResponse(
            server_time_utc=datetime.now(tz=UTC).isoformat(),
            uptime_seconds=time.monotonic() - state["started_at"],
        )

    @app.get("/readyz", response_model=ReadyResponse)
    def readyz() -> JSONResponse:
        state["ready_requests_total"] += 1
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

        ready = _is_ready()
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

    @app.get("/readyz-lite", response_model=ReadyzLiteResponse)
    def readyz_lite() -> ReadyzLiteResponse:
        state["readyz_lite_requests_total"] += 1
        return ReadyzLiteResponse(
            ready=_is_ready(),
            uptime_seconds=time.monotonic() - state["started_at"],
        )

    @app.get("/readyz-reason", response_model=ReadyzReasonResponse)
    def readyz_reason() -> ReadyzReasonResponse:
        state["readyz_reason_requests_total"] += 1
        index_path = state["index_path"]
        artifacts_dir = index_path.parent
        reasons: list[str] = []

        if state["rag"] is None:
            reasons.append("index_not_loaded")
        if not index_path.exists():
            reasons.append("index_missing")
        elif not index_path.is_file() or not os.access(index_path, os.R_OK):
            reasons.append("index_unreadable")
        if not artifacts_dir.exists() or not artifacts_dir.is_dir():
            reasons.append("artifacts_dir_missing")
        elif not os.access(artifacts_dir, os.W_OK | os.X_OK):
            reasons.append("artifacts_dir_not_writable")

        return ReadyzReasonResponse(
            ready=not reasons,
            reasons=reasons,
            index_path=str(index_path),
        )

    @app.get("/statusz", response_model=StatuszResponse)
    def statusz() -> StatuszResponse:
        state["statusz_requests_total"] += 1
        return StatuszResponse(
            ready=_is_ready(),
            uptime_seconds=time.monotonic() - state["started_at"],
            app_version=app.version,
        )

    @app.get("/meta-lite", response_model=MetaLiteResponse)
    def meta_lite() -> MetaLiteResponse:
        state["meta_lite_requests_total"] += 1
        return MetaLiteResponse(
            app_name=app.title,
            app_version=app.version,
            uptime_seconds=time.monotonic() - state["started_at"],
        )

    @app.get("/version", response_model=VersionResponse)
    def version() -> VersionResponse:
        state["version_requests_total"] += 1
        return VersionResponse(
            app_version=app.version,
            index_path=str(state["index_path"]),
        )

    @app.get("/build-info", response_model=BuildInfoResponse)
    def build_info() -> BuildInfoResponse:
        state["build_info_requests_total"] += 1
        return BuildInfoResponse(
            app_version=app.version,
            index_path=str(state["index_path"]),
            started_at=state["started_at_iso"],
        )

    @app.get("/build-lite", response_model=BuildLiteResponse)
    def build_lite() -> BuildLiteResponse:
        state["build_lite_requests_total"] += 1
        return BuildLiteResponse(
            app_version=app.version,
            started_at=state["started_at_iso"],
        )

    @app.get("/diag", response_model=DiagResponse)
    def diag() -> DiagResponse:
        state["diag_requests_total"] += 1
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

    @app.get("/diag-lite", response_model=DiagLiteResponse)
    def diag_lite() -> DiagLiteResponse:
        state["diag_lite_requests_total"] += 1
        rag = state["rag"]

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

        return DiagLiteResponse(
            status="ok",
            index_loaded=rag is not None,
            index_snapshot=index_snapshot,
        )

    @app.get("/openapi-lite", response_model=OpenApiLiteResponse)
    def openapi_lite() -> OpenApiLiteResponse:
        state["openapi_lite_requests_total"] += 1
        return OpenApiLiteResponse(
            status="ok",
            app_version=app.version,
            routes=_safe_route_summary(app),
        )

    @app.get("/routes-hash", response_model=RoutesHashResponse)
    def routes_hash() -> RoutesHashResponse:
        state["routes_hash_requests_total"] += 1
        routes = _safe_route_summary(app)
        return RoutesHashResponse(
            status="ok",
            algorithm="sha256",
            routes_hash=_stable_routes_hash(routes),
            routes_count=len(routes),
        )

    @app.get("/metrics")
    def metrics() -> Response:
        state["metrics_requests_total"] += 1
        return Response(
            content=_render_metrics(state),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get("/limits", response_model=LimitsResponse)
    def limits() -> LimitsResponse:
        state["limits_requests_total"] += 1
        return LimitsResponse(
            ask_query_max_chars=ASK_QUERY_MAX_CHARS,
            ask_top_k_max=ASK_TOP_K_MAX,
            doc_id_max_chars=DOC_ID_MAX_CHARS,
            ingest_text_max_chars=INGEST_TEXT_MAX_CHARS,
        )

    @app.get("/stats", response_model=StatsResponse)
    def stats() -> StatsResponse:
        state["stats_requests_total"] += 1
        ask_latency_samples = state["ask_latency_seconds"]
        ask_latency_avg_seconds = (
            sum(ask_latency_samples) / len(ask_latency_samples)
            if ask_latency_samples
            else 0.0
        )
        ingest_latency_samples = state["ingest_latency_seconds"]
        ingest_latency_avg_seconds = (
            sum(ingest_latency_samples) / len(ingest_latency_samples)
            if ingest_latency_samples
            else 0.0
        )

        counters = {
            "health": state["health_requests_total"],
            "healthz_lite": state["healthz_lite_requests_total"],
            "alivez": state["alivez_requests_total"],
            "echoz": state["echoz_requests_total"],
            "pingz": state["pingz_requests_total"],
            "timez": state["timez_requests_total"],
            "ready": state["ready_requests_total"],
            "readyz_lite": state["readyz_lite_requests_total"],
            "readyz_reason": state["readyz_reason_requests_total"],
            "statusz": state["statusz_requests_total"],
            "meta_lite": state["meta_lite_requests_total"],
            "ask": state["ask_requests_total"],
            "ask_errors": state["ask_errors_total"],
            "ask_safe": state["ask_safe_requests_total"],
            "ask_safe_errors": state["ask_safe_errors_total"],
            "ingest": state["ingest_requests_total"],
            "ingest_errors": state["ingest_errors_total"],
            "diag": state["diag_requests_total"],
            "diag_lite": state["diag_lite_requests_total"],
            "openapi_lite": state["openapi_lite_requests_total"],
            "routes_hash": state["routes_hash_requests_total"],
            "version": state["version_requests_total"],
            "build_info": state["build_info_requests_total"],
            "build_lite": state["build_lite_requests_total"],
            "metrics": state["metrics_requests_total"],
            "limits": state["limits_requests_total"],
            "stats": state["stats_requests_total"],
        }
        return StatsResponse(
            status="ok",
            uptime_seconds=time.monotonic() - state["started_at"],
            requests_total=sum(counters.values()),
            ask_latency_avg_seconds=ask_latency_avg_seconds,
            ask_latency_samples=len(ask_latency_samples),
            ingest_latency_avg_seconds=ingest_latency_avg_seconds,
            ingest_latency_samples=len(ingest_latency_samples),
            counters=counters,
        )

    @app.post("/ingest", response_model=IngestResponse)
    def ingest(req: IngestRequest) -> IngestResponse:
        state["ingest_requests_total"] += 1
        started = time.perf_counter()

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

        if req.replace_existing:
            rag.chunks = [c for c in rag.chunks if c.doc_id != req.doc_id] + chunks
        else:
            rag.chunks.extend(chunks)

        texts = [c.text for c in rag.chunks]
        rag._matrix = rag.vectorizer.fit_transform(texts) if texts else None
        rag._semantic_embeddings = rag._encode_semantic_texts(texts)
        rag.save(state["index_path"])
        _record_latency(state["ingest_latency_seconds"], time.perf_counter() - started)

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
        result = rag.answer_with_citations(
            req.query,
            top_k=req.top_k,
            min_score=req.min_score,
            doc_id=req.doc_id,
            doc_id_contains=req.doc_id_contains,
        )
        _record_latency(state["ask_latency_seconds"], time.perf_counter() - started)
        citations = citations_to_dict(result.citations)
        return AskResponse(
            answer=result.answer,
            citations=citations,
            citations_count=len(citations),
        )

    @app.post("/ask-safe", response_model=AskResponse)
    def ask_safe(req: AskRequest) -> AskResponse:
        state["ask_safe_requests_total"] += 1
        response = ask(req)
        if not response.citations:
            state["ask_safe_errors_total"] += 1
            raise HTTPException(
                status_code=404,
                detail=(
                    "no matching citations found for query; "
                    "relax min_score or adjust filters"
                ),
            )
        return response

    return app
