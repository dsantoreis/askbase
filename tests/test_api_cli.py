import json
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from rag_pipeline.api import create_app
from rag_pipeline.pipeline import IngestConfig, RAGPipeline


def test_api_health_metrics_and_ask(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text(
        "Internal KB: VPN issues require checking MFA enrollment first.",
        encoding="utf-8",
    )

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    health_payload = health.json()
    assert health_payload["status"] == "ok"
    assert health_payload["index_loaded"] is True

    healthz_lite = client.get("/healthz-lite")
    assert healthz_lite.status_code == 200
    healthz_lite_payload = healthz_lite.json()
    assert healthz_lite_payload["status"] == "ok"
    assert healthz_lite_payload["uptime_seconds"] >= 0

    alivez = client.get("/alivez")
    assert alivez.status_code == 200
    alivez_payload = alivez.json()
    assert alivez_payload["status"] == "alive"

    echoz = client.get("/echoz")
    assert echoz.status_code == 200
    echoz_payload = echoz.json()
    assert echoz_payload["status"] == "ok"
    assert echoz_payload["service"] == "RAG Pipeline Demo API"

    pingz = client.get("/pingz")
    assert pingz.status_code == 200
    pingz_payload = pingz.json()
    assert pingz_payload["status"] == "ok"
    assert pingz_payload["latency_ms"] >= 0
    assert datetime.fromisoformat(pingz_payload["timestamp_utc"]) is not None

    timez = client.get("/timez")
    assert timez.status_code == 200
    timez_payload = timez.json()
    assert timez_payload["uptime_seconds"] >= 0
    assert datetime.fromisoformat(timez_payload["server_time_utc"]) is not None

    version = client.get("/version")
    assert version.status_code == 200
    version_payload = version.json()
    assert version_payload["app_version"] == "1.2.0"
    assert version_payload["index_path"] == str(index)

    build_info = client.get("/build-info")
    assert build_info.status_code == 200
    build_info_payload = build_info.json()
    assert build_info_payload["app_version"] == "1.2.0"
    assert build_info_payload["index_path"] == str(index)
    assert build_info_payload["started_at"]
    assert datetime.fromisoformat(build_info_payload["started_at"]) is not None

    build_lite = client.get("/build-lite")
    assert build_lite.status_code == 200
    build_lite_payload = build_lite.json()
    assert build_lite_payload["app_version"] == "1.2.0"
    assert build_lite_payload["started_at"] == build_info_payload["started_at"]
    assert datetime.fromisoformat(build_lite_payload["started_at"]) is not None
    assert "index_path" not in build_lite_payload

    diag = client.get("/diag")
    assert diag.status_code == 200
    diag_payload = diag.json()
    assert diag_payload["status"] == "ok"
    assert diag_payload["index_loaded"] is True
    assert diag_payload["index_snapshot"]["chunks_count"] >= 1
    assert diag_payload["index_snapshot"]["unique_doc_ids_count"] >= 1
    assert "excerpt" not in str(diag_payload).lower()
    assert (
        "vpn issues require checking mfa enrollment first"
        not in str(diag_payload).lower()
    )

    diag_lite = client.get("/diag-lite")
    assert diag_lite.status_code == 200
    diag_lite_payload = diag_lite.json()
    assert diag_lite_payload["status"] == "ok"
    assert diag_lite_payload["index_loaded"] is True
    assert diag_lite_payload["index_snapshot"]["chunks_count"] >= 1
    assert diag_lite_payload["index_snapshot"]["unique_doc_ids_count"] >= 1
    assert "index_file" not in diag_lite_payload
    assert "artifacts_snapshot" not in diag_lite_payload

    ready = client.get("/readyz")
    assert ready.status_code == 200
    ready_payload = ready.json()
    assert ready_payload["status"] == "ready"
    assert ready_payload["index_loaded"] is True
    assert ready_payload["index_exists"] is True
    assert ready_payload["index_readable"] is True
    assert ready_payload["artifacts_dir_exists"] is True
    assert ready_payload["artifacts_dir_writable"] is True

    readyz_lite = client.get("/readyz-lite")
    assert readyz_lite.status_code == 200
    readyz_lite_payload = readyz_lite.json()
    assert readyz_lite_payload["ready"] is True
    assert readyz_lite_payload["uptime_seconds"] >= 0

    readyz_reason = client.get("/readyz-reason")
    assert readyz_reason.status_code == 200
    readyz_reason_payload = readyz_reason.json()
    assert readyz_reason_payload["ready"] is True
    assert readyz_reason_payload["reasons"] == []
    assert readyz_reason_payload["index_path"] == str(index)

    statusz = client.get("/statusz")
    assert statusz.status_code == 200
    statusz_payload = statusz.json()
    assert statusz_payload["ready"] is True
    assert statusz_payload["uptime_seconds"] >= 0
    assert statusz_payload["app_version"] == "1.2.0"

    meta_lite = client.get("/meta-lite")
    assert meta_lite.status_code == 200
    meta_lite_payload = meta_lite.json()
    assert meta_lite_payload["app_name"] == "RAG Pipeline Demo API"
    assert meta_lite_payload["app_version"] == "1.2.0"
    assert meta_lite_payload["uptime_seconds"] >= 0

    openapi_lite = client.get("/openapi-lite")
    assert openapi_lite.status_code == 200
    openapi_lite_payload = openapi_lite.json()
    assert openapi_lite_payload["status"] == "ok"
    assert openapi_lite_payload["app_version"] == "1.2.0"
    routes = {
        item["path"]: set(item["methods"]) for item in openapi_lite_payload["routes"]
    }
    assert routes["/health"] == {"GET"}
    assert routes["/healthz-lite"] == {"GET"}
    assert routes["/alivez"] == {"GET"}
    assert routes["/echoz"] == {"GET"}
    assert routes["/pingz"] == {"GET"}
    assert routes["/timez"] == {"GET"}
    assert routes["/readyz-lite"] == {"GET"}
    assert routes["/readyz-reason"] == {"GET"}
    assert routes["/statusz"] == {"GET"}
    assert routes["/meta-lite"] == {"GET"}
    assert routes["/build-lite"] == {"GET"}
    assert routes["/diag-lite"] == {"GET"}
    assert routes["/limits"] == {"GET"}
    assert routes["/ask"] == {"POST"}
    assert routes["/ask-safe"] == {"POST"}
    assert "openapi" not in openapi_lite_payload
    assert "components" not in str(openapi_lite_payload).lower()

    routes_hash = client.get("/routes-hash")
    assert routes_hash.status_code == 200
    routes_hash_payload = routes_hash.json()
    assert routes_hash_payload["status"] == "ok"
    assert routes_hash_payload["algorithm"] == "sha256"
    assert routes_hash_payload["routes_count"] == len(openapi_lite_payload["routes"])
    assert re.fullmatch(r"[0-9a-f]{64}", routes_hash_payload["routes_hash"]) is not None

    routes_hash_again = client.get("/routes-hash")
    assert routes_hash_again.status_code == 200
    assert routes_hash_again.json()["routes_hash"] == routes_hash_payload["routes_hash"]

    stats_before_ask = client.get("/stats")
    assert stats_before_ask.status_code == 200
    stats_before_ask_payload = stats_before_ask.json()
    assert stats_before_ask_payload["status"] == "ok"
    assert stats_before_ask_payload["uptime_seconds"] >= 0
    assert stats_before_ask_payload["ask_latency_samples"] == 0
    assert stats_before_ask_payload["ask_latency_avg_seconds"] == 0
    assert stats_before_ask_payload["ingest_latency_samples"] == 0
    assert stats_before_ask_payload["ingest_latency_avg_seconds"] == 0
    assert stats_before_ask_payload["counters"] == {
        "health": 1,
        "healthz_lite": 1,
        "alivez": 1,
        "echoz": 1,
        "pingz": 1,
        "timez": 1,
        "ready": 1,
        "readyz_lite": 1,
        "statusz": 1,
        "meta_lite": 1,
        "ask": 0,
        "ask_errors": 0,
        "ask_safe": 0,
        "ask_safe_errors": 0,
        "ingest": 0,
        "ingest_errors": 0,
        "diag": 1,
        "diag_lite": 1,
        "openapi_lite": 1,
        "routes_hash": 2,
        "version": 1,
        "build_info": 1,
        "build_lite": 1,
        "metrics": 0,
        "limits": 0,
        "stats": 1,
    }
    assert stats_before_ask_payload["requests_total"] == 19

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "rag_api_health_requests_total" in metrics.text
    assert "rag_api_version_requests_total 1" in metrics.text
    assert "rag_api_ask_safe_requests_total 0" in metrics.text
    assert "rag_api_metrics_requests_total 1" in metrics.text

    limits = client.get("/limits")
    assert limits.status_code == 200
    limits_payload = limits.json()
    assert limits_payload == {
        "ask_query_max_chars": 2000,
        "ask_top_k_max": 20,
        "doc_id_max_chars": 256,
        "ingest_text_max_chars": 200000,
    }

    res = client.post("/ask", json={"query": "How solve VPN issues?", "top_k": 2})
    assert res.status_code == 200
    body = res.json()
    assert "answer" in body
    assert "citations" in body
    assert len(body["citations"]) >= 1
    assert body["citations_count"] == len(body["citations"])

    min_score_filtered = client.post(
        "/ask",
        json={"query": "How solve VPN issues?", "top_k": 2, "min_score": 10.0},
    )
    assert min_score_filtered.status_code == 200
    min_score_filtered_payload = min_score_filtered.json()
    assert min_score_filtered_payload["citations"] == []
    assert min_score_filtered_payload["citations_count"] == 0
    assert "Não encontrei contexto relevante" in min_score_filtered_payload["answer"]

    metrics_after_ask = client.get("/metrics")
    assert "rag_api_ask_requests_total 2" in metrics_after_ask.text
    assert "rag_api_ingest_latency_avg_seconds" in metrics_after_ask.text

    stats_after_ask = client.get("/stats")
    assert stats_after_ask.status_code == 200
    stats_after_ask_payload = stats_after_ask.json()
    assert stats_after_ask_payload["counters"]["ask"] == 2
    assert stats_after_ask_payload["counters"]["ask_safe"] == 0
    assert stats_after_ask_payload["counters"]["ask_safe_errors"] == 0
    assert stats_after_ask_payload["counters"]["metrics"] == 2
    assert stats_after_ask_payload["counters"]["limits"] == 1
    assert stats_after_ask_payload["counters"]["stats"] == 2
    assert stats_after_ask_payload["ask_latency_samples"] == 2
    assert stats_after_ask_payload["ask_latency_avg_seconds"] >= 0
    assert stats_after_ask_payload["ingest_latency_samples"] == 0
    assert stats_after_ask_payload["ingest_latency_avg_seconds"] == 0
    assert stats_after_ask_payload["requests_total"] == 25


def test_api_rejects_blank_query_with_422(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("MFA reset runbook.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    res = client.post("/ask", json={"query": "   ", "top_k": 1})
    assert res.status_code == 422


def test_api_rejects_too_long_query_with_422(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("MFA reset runbook.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    res = client.post("/ask", json={"query": "x" * 2001, "top_k": 1})
    assert res.status_code == 422


def test_api_rejects_too_long_doc_filter_with_422(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("MFA reset runbook.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    res = client.post("/ask", json={"query": "MFA", "doc_id": "x" * 257})
    assert res.status_code == 422


def test_api_limits_endpoint_reports_contract(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("MFA reset runbook.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    limits = client.get("/limits")
    assert limits.status_code == 200
    assert limits.json() == {
        "ask_query_max_chars": 2000,
        "ask_top_k_max": 20,
        "doc_id_max_chars": 256,
        "ingest_text_max_chars": 200000,
    }


def test_api_ask_safe_requires_citations(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("Runbook for MFA enrollment reset.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    no_match = client.post(
        "/ask-safe",
        json={"query": "Unrelated query", "top_k": 2, "min_score": 10.0},
    )
    assert no_match.status_code == 404
    assert "no matching citations" in no_match.json()["detail"]

    matched = client.post("/ask-safe", json={"query": "MFA reset", "top_k": 2})
    assert matched.status_code == 200
    matched_payload = matched.json()
    assert matched_payload["citations"]

    stats = client.get("/stats")
    assert stats.status_code == 200
    stats_payload = stats.json()
    assert stats_payload["counters"]["ask_safe"] == 2
    assert stats_payload["counters"]["ask_safe_errors"] == 1


def test_api_rejects_blank_doc_id_with_422(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text(
        "Runbook: recurring MFA failures are fixed by resetting enrollment.",
        encoding="utf-8",
    )

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    res = client.post(
        "/ask",
        json={
            "query": "How to solve MFA failures?",
            "top_k": 1,
            "doc_id": "   ",
        },
    )
    assert res.status_code == 422


def test_api_rejects_blank_doc_id_contains_with_422(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text(
        "Runbook: recurring MFA failures are fixed by resetting enrollment.",
        encoding="utf-8",
    )

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    res = client.post(
        "/ask",
        json={
            "query": "How to solve MFA failures?",
            "top_k": 1,
            "doc_id_contains": "   ",
        },
    )
    assert res.status_code == 422


def test_api_rejects_blank_ingest_text_with_422(tmp_path: Path):
    app = create_app(str(tmp_path / "missing.pkl"))
    client = TestClient(app)

    res = client.post("/ingest", json={"doc_id": "runbook:mfa", "text": "   "})
    assert res.status_code == 422


def test_api_rejects_doc_id_and_doc_id_contains_together_with_422(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("MFA reset runbook.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    res = client.post(
        "/ask",
        json={
            "query": "How to solve MFA failures?",
            "top_k": 1,
            "doc_id": "runbook:mfa",
            "doc_id_contains": "runbook",
        },
    )
    assert res.status_code == 422


def test_api_rejects_blank_ingest_doc_id_with_422(tmp_path: Path):
    app = create_app(str(tmp_path / "missing.pkl"))
    client = TestClient(app)

    res = client.post("/ingest", json={"doc_id": "   ", "text": "MFA reset steps"})
    assert res.status_code == 422


def test_api_ask_without_index_returns_400(tmp_path: Path):
    app = create_app(str(tmp_path / "missing.pkl"))
    client = TestClient(app)

    diag = client.get("/diag")
    assert diag.status_code == 200
    diag_payload = diag.json()
    assert diag_payload["index_loaded"] is False
    assert diag_payload["index_file"]["exists"] is False
    assert diag_payload["index_snapshot"]["chunks_count"] == 0

    diag_lite = client.get("/diag-lite")
    assert diag_lite.status_code == 200
    diag_lite_payload = diag_lite.json()
    assert diag_lite_payload["index_loaded"] is False
    assert diag_lite_payload["index_snapshot"]["chunks_count"] == 0
    assert "index_file" not in diag_lite_payload

    ready = client.get("/readyz")
    assert ready.status_code == 503
    ready_payload = ready.json()
    assert ready_payload["status"] == "not_ready"
    assert ready_payload["index_loaded"] is False

    readyz_lite = client.get("/readyz-lite")
    assert readyz_lite.status_code == 200
    readyz_lite_payload = readyz_lite.json()
    assert readyz_lite_payload["ready"] is False
    assert readyz_lite_payload["uptime_seconds"] >= 0

    readyz_reason = client.get("/readyz-reason")
    assert readyz_reason.status_code == 200
    readyz_reason_payload = readyz_reason.json()
    assert readyz_reason_payload["ready"] is False
    assert "index_not_loaded" in readyz_reason_payload["reasons"]
    assert "index_missing" in readyz_reason_payload["reasons"]

    alivez = client.get("/alivez")
    assert alivez.status_code == 200
    assert alivez.json()["status"] == "alive"

    echoz = client.get("/echoz")
    assert echoz.status_code == 200
    echoz_payload = echoz.json()
    assert echoz_payload["status"] == "ok"
    assert echoz_payload["service"] == "RAG Pipeline Demo API"

    statusz = client.get("/statusz")
    assert statusz.status_code == 200
    statusz_payload = statusz.json()
    assert statusz_payload["ready"] is False
    assert statusz_payload["uptime_seconds"] >= 0
    assert statusz_payload["app_version"] == "1.2.0"

    meta_lite = client.get("/meta-lite")
    assert meta_lite.status_code == 200
    meta_lite_payload = meta_lite.json()
    assert meta_lite_payload["app_name"] == "RAG Pipeline Demo API"
    assert meta_lite_payload["app_version"] == "1.2.0"
    assert meta_lite_payload["uptime_seconds"] >= 0

    build_lite = client.get("/build-lite")
    assert build_lite.status_code == 200
    build_lite_payload = build_lite.json()
    assert build_lite_payload["app_version"] == "1.2.0"
    assert datetime.fromisoformat(build_lite_payload["started_at"]) is not None

    res = client.post("/ask", json={"query": "hello", "top_k": 1})
    assert res.status_code == 400

    stats = client.get("/stats")
    assert stats.status_code == 200
    stats_payload = stats.json()
    assert stats_payload["ask_latency_samples"] == 0
    assert stats_payload["ask_latency_avg_seconds"] == 0
    assert stats_payload["ingest_latency_samples"] == 0
    assert stats_payload["ingest_latency_avg_seconds"] == 0
    assert stats_payload["counters"] == {
        "health": 0,
        "healthz_lite": 0,
        "alivez": 1,
        "echoz": 1,
        "pingz": 0,
        "timez": 0,
        "ready": 1,
        "readyz_lite": 1,
        "statusz": 1,
        "meta_lite": 1,
        "ask": 1,
        "ask_errors": 1,
        "ask_safe": 0,
        "ask_safe_errors": 0,
        "ingest": 0,
        "ingest_errors": 0,
        "diag": 1,
        "diag_lite": 1,
        "openapi_lite": 0,
        "routes_hash": 0,
        "version": 0,
        "build_info": 0,
        "build_lite": 1,
        "metrics": 0,
        "limits": 0,
        "stats": 1,
    }
    assert stats_payload["requests_total"] == 12


def test_api_ingest_then_ask(tmp_path: Path):
    index = tmp_path / "api_ingest.pkl"
    app = create_app(str(index))
    client = TestClient(app)

    ingest = client.post(
        "/ingest",
        json={
            "doc_id": "runbook:mfa",
            "text": "Runbook: recurring MFA failures are fixed by resetting enrollment and confirming identity.",
        },
    )
    assert ingest.status_code == 200
    ingest_payload = ingest.json()
    assert ingest_payload["chunks_indexed"] >= 1
    assert Path(ingest_payload["index_path"]).exists()

    ingest_other = client.post(
        "/ingest",
        json={
            "doc_id": "runbook:vpn",
            "text": "VPN incidents are solved by validating network routes and certificate expiration.",
        },
    )
    assert ingest_other.status_code == 200

    ask = client.post("/ask", json={"query": "How to solve recurring MFA failures?"})
    assert ask.status_code == 200
    ask_payload = ask.json()
    assert "answer" in ask_payload
    assert len(ask_payload["citations"]) >= 1

    ask_exact_doc = client.post(
        "/ask",
        json={
            "query": "How to solve recurring MFA failures?",
            "doc_id": "runbook:mfa",
        },
    )
    assert ask_exact_doc.status_code == 200
    ask_exact_doc_payload = ask_exact_doc.json()
    assert len(ask_exact_doc_payload["citations"]) >= 1
    assert all(c["doc_id"] == "runbook:mfa" for c in ask_exact_doc_payload["citations"])

    ask_filtered = client.post(
        "/ask",
        json={
            "query": "How to solve recurring MFA failures?",
            "doc_id_contains": "runbook",
        },
    )
    assert ask_filtered.status_code == 200
    ask_filtered_payload = ask_filtered.json()
    assert len(ask_filtered_payload["citations"]) >= 1
    assert all(
        "runbook" in citation["doc_id"].lower()
        for citation in ask_filtered_payload["citations"]
    )

    stats = client.get("/stats")
    assert stats.status_code == 200
    stats_payload = stats.json()
    assert stats_payload["counters"]["ingest"] == 2
    assert stats_payload["counters"]["ingest_errors"] == 0
    assert stats_payload["counters"]["ask"] == 3
    assert stats_payload["counters"]["ask_errors"] == 0
    assert stats_payload["ask_latency_samples"] == 3
    assert stats_payload["ask_latency_avg_seconds"] >= 0
    assert stats_payload["ingest_latency_samples"] == 2
    assert stats_payload["ingest_latency_avg_seconds"] >= 0


def test_api_ingest_supports_append_mode(tmp_path: Path):
    index = tmp_path / "api_ingest_append.pkl"
    app = create_app(str(index))
    client = TestClient(app)

    first_ingest = client.post(
        "/ingest",
        json={
            "doc_id": "runbook:mfa",
            "text": "Runbook: first version for MFA reset workflow.",
        },
    )
    assert first_ingest.status_code == 200

    second_ingest = client.post(
        "/ingest",
        json={
            "doc_id": "runbook:mfa",
            "text": "Runbook: second version adds identity verification checklist.",
            "replace_existing": False,
        },
    )
    assert second_ingest.status_code == 200

    diag = client.get("/diag-lite")
    assert diag.status_code == 200
    diag_payload = diag.json()
    assert diag_payload["index_snapshot"]["chunks_count"] >= 2

    ask = client.post(
        "/ask",
        json={"query": "What changed in MFA workflow?", "doc_id": "runbook:mfa"},
    )
    assert ask.status_code == 200
    ask_payload = ask.json()
    assert len(ask_payload["citations"]) >= 1
    assert all(c["doc_id"] == "runbook:mfa" for c in ask_payload["citations"])


def test_cli_ingest_passes_semantic_flags(monkeypatch, tmp_path: Path):
    from rag_pipeline import cli as cli_module

    captured: dict[str, object] = {}

    class DummyRAGPipeline:
        def __init__(self, ingest_config, retrieval_config):
            captured["ingest_config"] = ingest_config
            captured["retrieval_config"] = retrieval_config

        def ingest_paths(self, paths):
            captured["paths"] = paths
            return 1

        def save(self, index):
            captured["index"] = index

    monkeypatch.setattr(cli_module, "RAGPipeline", DummyRAGPipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rag_pipeline.cli",
            "ingest",
            str(tmp_path),
            "--index",
            str(tmp_path / "semantic.pkl"),
            "--use-semantic",
            "--semantic-weight",
            "0.35",
            "--semantic-model",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ],
    )

    cli_module.main()

    retrieval = captured["retrieval_config"]
    assert retrieval.use_semantic is True
    assert retrieval.semantic_weight == 0.35
    assert (
        retrieval.semantic_model
        == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    assert captured["paths"] == [str(tmp_path)]


def test_cli_rejects_non_positive_top_k(tmp_path: Path):
    index = tmp_path / "missing.pkl"

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--top-k",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert ask.returncode != 0
    assert "must be >= 1" in ask.stderr


def test_cli_rejects_negative_min_score(tmp_path: Path):
    index = tmp_path / "missing.pkl"

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--min-score",
            "-0.1",
        ],
        capture_output=True,
        text=True,
    )

    assert ask.returncode != 0
    assert "must be >= 0" in ask.stderr


def test_cli_rejects_blank_query(tmp_path: Path):
    index = tmp_path / "missing.pkl"

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "   ",
            "--index",
            str(index),
        ],
        capture_output=True,
        text=True,
    )

    assert ask.returncode != 0
    assert "must not be blank" in ask.stderr


def test_cli_rejects_blank_doc_id(tmp_path: Path):
    index = tmp_path / "missing.pkl"

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--doc-id",
            "   ",
        ],
        capture_output=True,
        text=True,
    )

    assert ask.returncode != 0
    assert "must not be blank" in ask.stderr


def test_cli_rejects_blank_doc_id_contains(tmp_path: Path):
    index = tmp_path / "missing.pkl"

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--doc-id-contains",
            "   ",
        ],
        capture_output=True,
        text=True,
    )

    assert ask.returncode != 0
    assert "must not be blank" in ask.stderr


def test_cli_rejects_doc_id_and_doc_id_contains_together(tmp_path: Path):
    index = tmp_path / "missing.pkl"

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--doc-id",
            "runbook:mfa",
            "--doc-id-contains",
            "runbook",
        ],
        capture_output=True,
        text=True,
    )

    assert ask.returncode != 0
    assert "use either --doc-id or --doc-id-contains" in ask.stderr


def test_cli_ingest_and_ask_json(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ops.md").write_text(
        "For recurring MFA failures, reset enrollment and validate user identity first.",
        encoding="utf-8",
    )
    (docs / "vpn.md").write_text(
        "VPN troubleshooting focuses on certificate status and network routes.",
        encoding="utf-8",
    )

    index = tmp_path / "rag_cli.pkl"

    ingest = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ingest",
            str(docs),
            "--index",
            str(index),
            "--chunk-size",
            "80",
            "--overlap",
            "10",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Indexed" in ingest.stdout
    assert index.exists()

    ask = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--top-k",
            "2",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(ask.stdout)
    assert "answer" in payload
    assert isinstance(payload.get("citations"), list)
    assert len(payload["citations"]) >= 1

    ask_filtered = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--top-k",
            "2",
            "--min-score",
            "10",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    filtered_payload = json.loads(ask_filtered.stdout)
    assert filtered_payload["citations"] == []
    assert "Não encontrei contexto relevante" in filtered_payload["answer"]

    ask_doc_exact = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--top-k",
            "2",
            "--doc-id",
            str(docs / "ops.md"),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    doc_exact_payload = json.loads(ask_doc_exact.stdout)
    assert len(doc_exact_payload["citations"]) >= 1
    assert all(
        c["doc_id"] == str(docs / "ops.md") for c in doc_exact_payload["citations"]
    )

    ask_doc_filter = subprocess.run(
        [
            sys.executable,
            "-m",
            "rag_pipeline.cli",
            "ask",
            "How to fix recurring MFA failures?",
            "--index",
            str(index),
            "--top-k",
            "2",
            "--doc-id-contains",
            "ops",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    doc_filter_payload = json.loads(ask_doc_filter.stdout)
    assert len(doc_filter_payload["citations"]) >= 1
    assert all("ops" in c["doc_id"].lower() for c in doc_filter_payload["citations"])


def test_api_retains_only_recent_latency_samples(tmp_path: Path, monkeypatch):
    import rag_pipeline.api as api_module

    monkeypatch.setattr(api_module, "LATENCY_HISTORY_LIMIT", 3)

    index = tmp_path / "api_latency_limit.pkl"
    app = create_app(str(index))
    client = TestClient(app)

    for idx in range(4):
        ingest_res = client.post(
            "/ingest",
            json={
                "doc_id": f"runbook:{idx}",
                "text": f"Runbook {idx}: recurring MFA failure resolution with identity checks.",
            },
        )
        assert ingest_res.status_code == 200

    for _ in range(5):
        ask_res = client.post(
            "/ask",
            json={"query": "How to resolve recurring MFA failures?", "top_k": 1},
        )
        assert ask_res.status_code == 200

    stats = client.get("/stats")
    assert stats.status_code == 200
    payload = stats.json()
    assert payload["ingest_latency_samples"] == 3
    assert payload["ask_latency_samples"] == 3


def test_api_ingest_recomputes_semantic_embeddings(tmp_path: Path, monkeypatch):
    class FakeSentenceTransformer:
        def __init__(self, *_args, **_kwargs):
            pass

        def encode(self, texts):
            vectors = {
                "alpha policy document": [1.0, 0.0],
                "beta runbook document": [0.0, 1.0],
                "beta runbook": [0.0, 1.0],
            }
            return [vectors.get(text, [0.0, 0.0]) for text in texts]

    fake_module = type(
        "_FakeSentenceModule", (), {"SentenceTransformer": FakeSentenceTransformer}
    )
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    seed_doc = tmp_path / "seed.txt"
    seed_doc.write_text("alpha policy document", encoding="utf-8")
    index = tmp_path / "rag.pkl"

    rag = RAGPipeline(
        ingest_config=IngestConfig(chunk_size=80, overlap=10, min_chars=5),
    )
    rag.retrieval_config.use_semantic = True
    rag.retrieval_config.lexical_weight = 0.0
    rag.retrieval_config.keyword_weight = 0.0
    rag.retrieval_config.semantic_weight = 1.0
    rag.retrieval_config.rerank_boost = 0.0
    rag.ingest_paths([seed_doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    ingest_res = client.post(
        "/ingest",
        json={"doc_id": "api:beta", "text": "beta runbook document"},
    )
    assert ingest_res.status_code == 200

    ask_res = client.post(
        "/ask",
        json={"query": "beta runbook", "top_k": 1},
    )
    assert ask_res.status_code == 200
    ask_payload = ask_res.json()
    assert ask_payload["citations"]
    assert ask_payload["citations"][0]["doc_id"] == "api:beta"
