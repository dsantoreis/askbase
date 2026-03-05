from __future__ import annotations

import json
from pathlib import Path

from .pipeline import RAGPipeline


def evaluate_context_precision(index_path: str | Path, dataset_path: str | Path, k: int = 3) -> dict:
    rag = RAGPipeline.load(index_path)
    rows = _read_jsonl(dataset_path)
    if not rows:
        raise ValueError("empty evaluation dataset")

    per_query = []
    for row in rows:
        query = row["query"]
        relevant = set(row["relevant_doc_ids"])
        hits = rag.retrieve(query, top_k=k)
        predicted = [hit.chunk.doc_id for hit in hits]
        correct = sum(1 for doc_id in predicted if doc_id in relevant)
        precision = correct / max(len(predicted), 1)
        per_query.append({"query": query, "precision": precision, "predicted": predicted})

    return {
        "metric": f"context_precision@{k}",
        "value": sum(item["precision"] for item in per_query) / len(per_query),
        "samples": len(per_query),
        "details": per_query,
    }


def _read_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "query" not in row or "relevant_doc_ids" not in row:
                raise ValueError("each row requires query and relevant_doc_ids")
            rows.append(row)
    return rows
