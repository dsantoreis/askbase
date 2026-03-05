from pathlib import Path

import pytest

from rag_pipeline.pipeline import RAGPipeline


def test_missing_documents_raise(tmp_path: Path) -> None:
    rag = RAGPipeline()
    with pytest.raises(ValueError, match="path not found"):
        rag.ingest([tmp_path / "missing"])


def test_deterministic_retrieval_with_fixture_docs(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "vpn.txt").write_text("VPN reset token rotation runbook and split tunnel policy", encoding="utf-8")
    (docs / "db.txt").write_text("Database migration rollback checklist and backup verification", encoding="utf-8")

    rag = RAGPipeline(chunk_size=30, overlap=10)
    rag.ingest([docs])

    hits_a = rag.retrieve("token rotation policy", top_k=2)
    hits_b = rag.retrieve("token rotation policy", top_k=2)

    assert [h.chunk.doc_id for h in hits_a] == [h.chunk.doc_id for h in hits_b]
    assert hits_a[0].chunk.doc_id.endswith("vpn.txt")


def test_ask_returns_verifiable_citations(tmp_path: Path) -> None:
    doc = tmp_path / "policy.md"
    doc.write_text("Incident policy requires encrypted evidence retention for 90 days.", encoding="utf-8")

    rag = RAGPipeline(chunk_size=25, overlap=5)
    rag.ingest([doc])

    answer = rag.ask("What is evidence retention policy?", top_k=1)

    assert "Answer grounded" in answer.text
    assert answer.citations
    assert answer.citations[0].doc_id.endswith("policy.md")
    assert answer.citations[0].score >= 0.0


def test_retrieve_rejects_invalid_top_k(tmp_path: Path) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("SRE runbook for incident command and postmortem workflow.", encoding="utf-8")

    rag = RAGPipeline()
    rag.ingest([doc])

    with pytest.raises(ValueError, match="top_k must be >= 1"):
        rag.retrieve("incident command", top_k=0)

