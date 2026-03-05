from pathlib import Path

from fastapi.testclient import TestClient

from rag_pipeline.api import create_app
from rag_pipeline.pipeline import RAGPipeline


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

    ask = client.post("/ask", json={"query": "when rotate keys", "top_k": 1})
    assert ask.status_code == 200
    payload = ask.json()
    assert payload["citations_count"] == 1
