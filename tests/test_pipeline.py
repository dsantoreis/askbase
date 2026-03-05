import json
from pathlib import Path

import pytest

from rag_pipeline.pipeline import IngestConfig, RAGPipeline


@pytest.fixture
def sample_docs(tmp_path: Path) -> list[Path]:
    a = tmp_path / "policy.md"
    b = tmp_path / "support.txt"
    a.write_text(
        "Compliance policy requires annual review. Audit evidence must be stored for 7 years.",
        encoding="utf-8",
    )
    b.write_text(
        "Support playbook: reset MFA, verify identity, escalate L2 when repeated failures happen.",
        encoding="utf-8",
    )
    return [a, b]


def test_ingest_retrieve_answer(sample_docs: list[Path]):
    rag = RAGPipeline(
        ingest_config=IngestConfig(chunk_size=90, overlap=20, chunk_strategy="char"),
    )
    n = rag.ingest_paths(sample_docs)
    assert n > 0

    hits = rag.retrieve("How long keep audit evidence?", top_k=2)
    assert hits
    assert hits[0]["score"] >= hits[-1]["score"]

    answer = rag.answer("What does compliance require?")
    assert "contexto" in answer.lower() or "compliance" in answer.lower()


def test_answer_includes_citations(sample_docs: list[Path]):
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=100, overlap=10))
    rag.ingest_paths(sample_docs)

    result = rag.answer_with_citations("Where to store audit evidence?", top_k=2)

    assert "Referências" in result.answer
    assert len(result.citations) >= 1
    assert result.citations[0].doc_id.endswith("policy.md")


def test_persist_load_and_eval(sample_docs: list[Path], tmp_path: Path):
    index = tmp_path / "idx.pkl"
    eval_data = tmp_path / "eval.jsonl"

    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=100, overlap=10))
    rag.ingest_paths(sample_docs)
    rag.save(index)

    eval_data.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "query": "Where to store audit evidence?",
                        "relevant_doc_ids": [str(sample_docs[0])],
                    }
                ),
                json.dumps(
                    {
                        "query": "When escalate support cases?",
                        "relevant_doc_ids": [str(sample_docs[1])],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    loaded = RAGPipeline.load(index)
    report = loaded.evaluate_precision_at_k(eval_data, k=2)

    assert report["metric"] == "precision@2"
    assert report["samples"] == 2
    assert 0.0 <= report["value"] <= 1.0


def test_ingest_validation_rejects_large_file(tmp_path: Path):
    big = tmp_path / "big.txt"
    big.write_text("a" * 2048, encoding="utf-8")

    rag = RAGPipeline(ingest_config=IngestConfig(max_file_mb=0))
    with pytest.raises(ValueError, match="file too large"):
        rag.ingest_paths([big])


def test_deduplicate_same_content(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    content = "same content for deduplication checks in ingestion pipeline"
    a.write_text(content, encoding="utf-8")
    b.write_text(content, encoding="utf-8")

    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=80, overlap=10))
    count = rag.ingest_paths([a, b])

    assert count > 0
    assert len({c.doc_id for c in rag.chunks}) == 1
