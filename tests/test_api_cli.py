from pathlib import Path

from fastapi.testclient import TestClient

from rag_pipeline.api import create_app
from rag_pipeline.pipeline import IngestConfig, RAGPipeline


def test_api_health_and_ask(tmp_path: Path):
    doc = tmp_path / "kb.txt"
    doc.write_text("Internal KB: VPN issues require checking MFA enrollment first.", encoding="utf-8")

    index = tmp_path / "rag.pkl"
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    rag.ingest_paths([doc])
    rag.save(index)

    app = create_app(str(index))
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    res = client.post("/ask", json={"query": "How solve VPN issues?", "top_k": 2})
    assert res.status_code == 200
    assert "answer" in res.json()


def test_api_ask_without_index_returns_400(tmp_path: Path):
    app = create_app(str(tmp_path / "missing.pkl"))
    client = TestClient(app)

    res = client.post("/ask", json={"query": "hello", "top_k": 1})
    assert res.status_code == 400
