import json
from pathlib import Path

import pytest

from rag_pipeline.pipeline import IngestConfig, RAGPipeline, RetrievalConfig


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


def test_retrieve_rejects_non_positive_top_k(sample_docs: list[Path]):
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=90, overlap=20))
    rag.ingest_paths(sample_docs)

    with pytest.raises(ValueError, match="top_k must be >= 1"):
        rag.retrieve("any query", top_k=0)


def test_retrieve_rejects_negative_min_score(sample_docs: list[Path]):
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=90, overlap=20))
    rag.ingest_paths(sample_docs)

    with pytest.raises(ValueError, match="min_score must be >= 0"):
        rag.retrieve("any query", min_score=-0.01)


def test_retrieve_respects_min_score_threshold(sample_docs: list[Path]):
    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=90, overlap=20))
    rag.ingest_paths(sample_docs)

    baseline_hits = rag.retrieve("audit evidence retention", top_k=3)
    assert baseline_hits

    threshold = max(hit["score"] for hit in baseline_hits) + 0.01
    filtered_hits = rag.retrieve("audit evidence retention", top_k=3, min_score=threshold)
    assert filtered_hits == []


def test_evaluate_rejects_non_positive_k(sample_docs: list[Path], tmp_path: Path):
    index = tmp_path / "idx.pkl"
    eval_data = tmp_path / "eval.jsonl"

    rag = RAGPipeline(ingest_config=IngestConfig(chunk_size=100, overlap=10))
    rag.ingest_paths(sample_docs)
    rag.save(index)

    eval_data.write_text(
        json.dumps(
            {
                "query": "Where to store audit evidence?",
                "relevant_doc_ids": [str(sample_docs[0])],
            }
        ),
        encoding="utf-8",
    )

    loaded = RAGPipeline.load(index)
    with pytest.raises(ValueError, match="k must be >= 1"):
        loaded.evaluate_precision_at_k(eval_data, k=0)


def test_semantic_retrieval_can_drive_ranking(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    car = docs / "car.txt"
    cloud = docs / "cloud.txt"
    car.write_text("automobile handbook", encoding="utf-8")
    cloud.write_text("cloud infrastructure", encoding="utf-8")

    class FakeSemanticModel:
        def encode(self, texts):
            mapping = {
                "automobile handbook": [1.0, 0.0],
                "cloud infrastructure": [0.0, 1.0],
                "car guide": [1.0, 0.0],
            }
            return [mapping.get(text, [0.0, 0.0]) for text in texts]

    rag = RAGPipeline(
        ingest_config=IngestConfig(chunk_size=80, overlap=10, min_chars=5),
        retrieval_config=RetrievalConfig(
            lexical_weight=0.0,
            keyword_weight=0.0,
            semantic_weight=1.0,
            rerank_boost=0.0,
            use_semantic=True,
        ),
    )
    rag._semantic_model = FakeSemanticModel()
    rag.ingest_paths([docs])

    hits = rag.retrieve("car guide", top_k=1)

    assert hits
    assert hits[0]["chunk"].doc_id.endswith("car.txt")
    assert hits[0]["semantic_score"] > 0.9
