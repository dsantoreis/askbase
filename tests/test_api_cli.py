import json
import subprocess
import sys
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

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "rag_api_health_requests_total" in metrics.text

    res = client.post("/ask", json={"query": "How solve VPN issues?", "top_k": 2})
    assert res.status_code == 200
    body = res.json()
    assert "answer" in body
    assert "citations" in body
    assert len(body["citations"]) >= 1

    metrics_after_ask = client.get("/metrics")
    assert "rag_api_ask_requests_total 1" in metrics_after_ask.text


def test_api_ask_without_index_returns_400(tmp_path: Path):
    app = create_app(str(tmp_path / "missing.pkl"))
    client = TestClient(app)

    res = client.post("/ask", json={"query": "hello", "top_k": 1})
    assert res.status_code == 400


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

    ask = client.post("/ask", json={"query": "How to solve recurring MFA failures?"})
    assert ask.status_code == 200
    ask_payload = ask.json()
    assert "answer" in ask_payload
    assert len(ask_payload["citations"]) >= 1
    assert ask_payload["citations"][0]["doc_id"] == "runbook:mfa"


def test_cli_ingest_and_ask_json(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ops.md").write_text(
        "For recurring MFA failures, reset enrollment and validate user identity first.",
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
