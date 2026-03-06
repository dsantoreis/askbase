from pathlib import Path

from fastapi.testclient import TestClient

from rag_pipeline.api import create_app
from rag_pipeline.pipeline import RAGPipeline

ADMIN = {"Authorization": "Bearer admin-demo-token"}
USER = {"Authorization": "Bearer user-demo-token"}


def test_api_health_and_ask_flow(tmp_path: Path) -> None:
    doc = tmp_path / "guide.txt"
    doc.write_text("Runbook: rotate keys every 30 days.", encoding="utf-8")

    index = tmp_path / "idx.pkl"
    rag = RAGPipeline()
    rag.ingest([doc])
    rag.save(index)

    app = create_app(index_path=str(index))
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["index_loaded"] is True

    ask = client.post("/ask", json={"query": "when rotate keys", "top_k": 1}, headers=USER)
    assert ask.status_code == 200
    payload = ask.json()
    assert payload["citations_count"] == 1
    assert payload["rate_limit"]["remaining"] >= 0


def test_admin_stats_requires_admin(tmp_path: Path) -> None:
    index = tmp_path / "idx.pkl"
    app = create_app(index_path=str(index))
    client = TestClient(app)

    no_auth = client.get("/admin/stats")
    assert no_auth.status_code == 401

    forbidden = client.get("/admin/stats", headers=USER)
    assert forbidden.status_code == 403

    ok = client.get("/admin/stats", headers=ADMIN)
    assert ok.status_code == 200


def test_metrics_exposed(tmp_path: Path) -> None:
    app = create_app(index_path=str(tmp_path / "idx.pkl"))
    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "rag_http_requests_total" in res.text


def test_health_head_probe(tmp_path: Path) -> None:
    app = create_app(index_path=str(tmp_path / "idx.pkl"))
    client = TestClient(app)
    res = client.head("/health")
    assert res.status_code == 200
    assert res.text == ""


def test_statusz_reports_version_and_uptime(tmp_path: Path) -> None:
    app = create_app(index_path=str(tmp_path / "idx.pkl"))
    client = TestClient(app)

    status = client.get("/statusz")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "ok"
    assert body["version"] == "4.0.0"
    assert isinstance(body["uptime_sec"], int)
    assert body["uptime_sec"] >= 0

    head = client.head("/statusz")
    assert head.status_code == 200
    assert head.text == ""


def test_readyz_reflects_index_state(tmp_path: Path) -> None:
    index = tmp_path / "idx.pkl"
    app = create_app(index_path=str(index))
    client = TestClient(app)

    cold = client.get("/readyz")
    assert cold.status_code == 200
    assert cold.json()["ready"] is False
    assert cold.json()["chunks_loaded"] == 0

    doc = tmp_path / "ready-doc.txt"
    doc.write_text("SOC2 controls evidence and audit schedule", encoding="utf-8")
    rag = RAGPipeline()
    rag.ingest([doc])
    rag.save(index)

    app_warm = create_app(index_path=str(index))
    client_warm = TestClient(app_warm)

    warm = client_warm.get("/readyz")
    assert warm.status_code == 200
    assert warm.json()["ready"] is True
    assert warm.json()["chunks_loaded"] > 0

    head = client_warm.head("/readyz")
    assert head.status_code == 200
    assert head.text == ""
