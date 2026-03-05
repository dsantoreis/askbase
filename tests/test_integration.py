import json
from pathlib import Path

from rag_pipeline.evaluation import evaluate_context_precision
from rag_pipeline.pipeline import RAGPipeline


def test_end_to_end_ingest_ask_evaluate(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    a = docs / "hr.txt"
    b = docs / "security.txt"
    a.write_text("Vacation policy: carry-over up to five days.", encoding="utf-8")
    b.write_text("Security policy: MFA required for privileged access.", encoding="utf-8")

    index_path = tmp_path / "artifacts" / "rag.pkl"

    rag = RAGPipeline()
    rag.ingest([docs])
    rag.save(index_path)

    out = rag.ask("Is MFA required?", top_k=2)
    assert out.citations

    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        json.dumps({"query": "MFA required", "relevant_doc_ids": [str(b)]}) + "\n",
        encoding="utf-8",
    )

    report = evaluate_context_precision(index_path, dataset, k=2)
    assert report["metric"] == "context_precision@2"
    assert report["samples"] == 1
    assert 0.0 <= report["value"] <= 1.0
