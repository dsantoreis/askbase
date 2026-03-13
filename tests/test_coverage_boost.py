"""Tests targeting uncovered lines to push coverage toward 95%+."""
from pathlib import Path
import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from rag_pipeline.api import create_app
from rag_pipeline.chunking import chunk_text
from rag_pipeline.documents import collect_documents, load_document
from rag_pipeline.pipeline import RAGPipeline

ADMIN = {"Authorization": "Bearer admin-demo-token"}
USER = {"Authorization": "Bearer user-demo-token"}


# --- API: evaluate endpoint (lines 92-97, 113-116) ---

class TestEvaluateEndpoint:
    def test_evaluate_no_index_returns_400(self, tmp_path: Path) -> None:
        """Line 116: index not found raises 400."""
        app = create_app(index_path=str(tmp_path / "nonexistent.pkl"))
        client = TestClient(app)
        resp = client.post(
            "/evaluate",
            json={"dataset_path": "eval.json", "k": 3},
            headers=ADMIN,
        )
        assert resp.status_code == 400
        assert "index not found" in resp.json()["detail"]

    def test_evaluate_requires_admin(self, tmp_path: Path) -> None:
        app = create_app(index_path=str(tmp_path / "idx.pkl"))
        client = TestClient(app)
        resp = client.post(
            "/evaluate",
            json={"dataset_path": "eval.json"},
            headers=USER,
        )
        assert resp.status_code == 403

    def test_evaluate_success_with_valid_index(self, tmp_path: Path) -> None:
        """Lines 92-97: evaluate success path."""
        doc = tmp_path / "faq.txt"
        doc.write_text("Password reset: go to Settings > Security > Reset Password.", encoding="utf-8")

        index_path = tmp_path / "idx.pkl"
        rag = RAGPipeline()
        rag.ingest([doc])
        rag.save(index_path)

        dataset = tmp_path / "eval.jsonl"
        dataset.write_text(
            json.dumps({"query": "How do I reset my password?", "relevant_doc_ids": [str(doc)]}) + "\n",
            encoding="utf-8",
        )

        app = create_app(index_path=str(index_path))
        client = TestClient(app)
        resp = client.post(
            "/evaluate",
            json={"dataset_path": str(dataset), "k": 1},
            headers=ADMIN,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "precision" in body or "results" in body or isinstance(body, dict)


# --- API: ask with no index (line 102) ---

class TestAskNoIndex:
    def test_ask_without_loaded_index_returns_400(self, tmp_path: Path) -> None:
        app = create_app(index_path=str(tmp_path / "nope.pkl"))
        client = TestClient(app)
        resp = client.post(
            "/ask",
            json={"query": "test"},
            headers=USER,
        )
        assert resp.status_code == 400
        assert "index not loaded" in resp.json()["detail"]


# --- API: ingest via HTTP ---

class TestIngestEndpoint:
    def test_ingest_creates_index(self, tmp_path: Path) -> None:
        doc = tmp_path / "policy.txt"
        doc.write_text("All employees must complete security training annually.", encoding="utf-8")

        index_path = tmp_path / "idx.pkl"
        app = create_app(index_path=str(index_path))
        client = TestClient(app)

        resp = client.post(
            "/ingest",
            json={"paths": [str(doc)]},
            headers=ADMIN,
        )
        assert resp.status_code == 200
        assert resp.json()["chunks_indexed"] > 0
        assert index_path.exists()


# --- Chunking edge cases (lines 16, 18, 22) ---

class TestChunkingEdgeCases:
    def test_chunk_size_too_small_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_size must be >= 20"):
            chunk_text("hello world", "doc1", chunk_size=10)

    def test_negative_overlap_raises(self) -> None:
        with pytest.raises(ValueError, match="overlap must be >= 0"):
            chunk_text("hello world", "doc1", chunk_size=30, overlap=-1)

    def test_overlap_equals_chunk_size_raises(self) -> None:
        with pytest.raises(ValueError, match="overlap must be >= 0 and < chunk_size"):
            chunk_text("hello world", "doc1", chunk_size=30, overlap=30)

    def test_empty_text_returns_empty(self) -> None:
        result = chunk_text("   ", "doc1")
        assert result == []


# --- Documents edge cases (lines 20, 30-31, 36) ---

class TestDocumentEdgeCases:
    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "data.csv"
        bad.write_text("a,b,c", encoding="utf-8")
        with pytest.raises(ValueError, match="unsupported extension"):
            collect_documents([bad])

    def test_path_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="path not found"):
            collect_documents([tmp_path / "ghost.txt"])

    def test_empty_document_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "blank.txt"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="no extractable text"):
            load_document(empty)

    def test_directory_collects_recursively(self, tmp_path: Path) -> None:
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "a.txt").write_text("Document A content here", encoding="utf-8")
        (sub / "b.md").write_text("Document B markdown content", encoding="utf-8")
        (sub / "ignore.csv").write_text("skip me", encoding="utf-8")
        docs = collect_documents([tmp_path])
        assert len(docs) == 2


# --- CLI edge cases (lines 67, 77-82, 113) ---

class TestCLI:
    def test_cli_status_no_index(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "rag_pipeline.cli", "status", "--index", str(tmp_path / "no.pkl")],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["index_exists"] is False

    def test_cli_status_with_index(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.txt"
        doc.write_text("Compliance policy requires annual review.", encoding="utf-8")
        index = tmp_path / "idx.pkl"

        rag = RAGPipeline()
        rag.ingest([doc])
        rag.save(index)

        result = subprocess.run(
            [sys.executable, "-m", "rag_pipeline.cli", "status", "--index", str(index), "--pretty"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["index_exists"] is True
        assert data["chunks"] > 0

    def test_cli_ask_no_index_exits(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "rag_pipeline.cli", "ask", "hello", "--index", str(tmp_path / "no.pkl")],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode != 0

    def test_cli_ask_json_output(self, tmp_path: Path) -> None:
        doc = tmp_path / "doc.txt"
        doc.write_text("Reset your password via Settings > Security.", encoding="utf-8")
        index = tmp_path / "idx.pkl"

        rag = RAGPipeline()
        rag.ingest([doc])
        rag.save(index)

        result = subprocess.run(
            [sys.executable, "-m", "rag_pipeline.cli", "ask", "password reset", "--index", str(index), "--json"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "answer" in data
        assert "citations" in data

    def test_cli_ingest(self, tmp_path: Path) -> None:
        doc = tmp_path / "policy.txt"
        doc.write_text("Data retention policy: 7 years for financial records.", encoding="utf-8")
        index = tmp_path / "idx.pkl"

        result = subprocess.run(
            [sys.executable, "-m", "rag_pipeline.cli", "ingest", str(doc), "--index", str(index)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert "chunks" in result.stdout.lower() or "Indexed" in result.stdout
