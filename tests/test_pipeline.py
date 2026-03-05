from pathlib import Path
from rag_pipeline.pipeline import RAGPipeline


def test_rag_ingest_retrieve_answer(tmp_path: Path):
    doc = tmp_path / "doc.txt"
    doc.write_text("Python é uma linguagem. RAG usa retrieval para trazer contexto relevante.", encoding="utf-8")

    rag = RAGPipeline()
    n = rag.ingest_paths([doc], chunk_size=80, overlap=20)
    assert n > 0

    hits = rag.retrieve("O que RAG usa para contexto?", top_k=2)
    assert hits

    answer = rag.answer("Como funciona RAG?")
    assert "contexto" in answer.lower() or "retrieval" in answer.lower()
