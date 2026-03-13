"""Final coverage push targeting remaining uncovered lines."""
import json
import logging
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from rag_pipeline.documents import load_document
from rag_pipeline.evaluation import evaluate_context_precision
from rag_pipeline.logging_utils import JsonFormatter
from rag_pipeline.observability import configure_logging
from rag_pipeline.pipeline import RAGPipeline, dump_eval, citations_to_dict, Citation
from rag_pipeline.retrieval import Retriever
from rag_pipeline.security import AuthManager, AuthContext, InMemoryRateLimiter


class TestPipelineLoadVersionMismatch:
    def test_load_version_mismatch_raises(self, tmp_path: Path) -> None:
        """pipeline.py line 96: index version mismatch."""
        import pickle
        idx = tmp_path / "old.pkl"
        with idx.open("wb") as fh:
            pickle.dump({"index_version": "0.0.0-invalid"}, fh)
        with pytest.raises(ValueError, match="index version mismatch"):
            RAGPipeline.load(idx)


class TestPipelineAskNoHits:
    def test_ask_returns_no_context_when_empty(self) -> None:
        """pipeline.py line 52: no hits returns fallback answer."""
        rag = RAGPipeline()
        answer = rag.ask("anything")
        assert "no supporting context" in answer.text.lower()


class TestDumpEval:
    def test_dump_eval_writes_jsonl(self, tmp_path: Path) -> None:
        """pipeline.py lines 109-113."""
        rows = [
            {"query": "test", "precision": 0.8},
            {"query": "test2", "precision": 1.0},
        ]
        out = tmp_path / "sub" / "eval.jsonl"
        dump_eval(out, rows)
        assert out.exists()
        lines = out.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["precision"] == 0.8


class TestCitationsToDict:
    def test_converts_citations(self) -> None:
        cits = [Citation(doc_id="d1", start_char=0, end_char=10, score=0.9, excerpt="hello")]
        result = citations_to_dict(cits)
        assert len(result) == 1
        assert result[0]["doc_id"] == "d1"
        assert result[0]["score"] == 0.9


class TestEvaluationEdgeCases:
    def test_evaluate_empty_dataset_raises(self, tmp_path: Path) -> None:
        """evaluation.py line 13: empty dataset."""
        doc = tmp_path / "doc.txt"
        doc.write_text("Some content for the index.", encoding="utf-8")
        idx = tmp_path / "idx.pkl"
        rag = RAGPipeline()
        rag.ingest([doc])
        rag.save(idx)

        ds = tmp_path / "empty.jsonl"
        ds.write_text("", encoding="utf-8")

        with pytest.raises(ValueError, match="empty evaluation dataset"):
            evaluate_context_precision(str(idx), str(ds))

    def test_evaluate_missing_fields_raises(self, tmp_path: Path) -> None:
        """evaluation.py lines 39, 42: missing relevant_doc_ids."""
        doc = tmp_path / "doc.txt"
        doc.write_text("Indexed content here for tests.", encoding="utf-8")
        idx = tmp_path / "idx.pkl"
        rag = RAGPipeline()
        rag.ingest([doc])
        rag.save(idx)

        ds = tmp_path / "bad.jsonl"
        ds.write_text(json.dumps({"query": "test"}) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="each row requires query and relevant_doc_ids"):
            evaluate_context_precision(str(idx), str(ds))

    def test_evaluate_skips_blank_lines(self, tmp_path: Path) -> None:
        """evaluation.py line 39: skip blank lines in JSONL."""
        doc = tmp_path / "doc.txt"
        doc.write_text("Password reset via Settings menu.", encoding="utf-8")
        idx = tmp_path / "idx.pkl"
        rag = RAGPipeline()
        rag.ingest([doc])
        rag.save(idx)

        ds = tmp_path / "eval.jsonl"
        ds.write_text(
            "\n" + json.dumps({"query": "password", "relevant_doc_ids": [str(doc)]}) + "\n\n",
            encoding="utf-8",
        )

        result = evaluate_context_precision(str(idx), str(ds), k=1)
        assert isinstance(result, dict)


class TestLoggingUtils:
    def test_json_formatter_with_exception(self) -> None:
        """logging_utils.py line 17: exc_info branch."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="boom", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" not in data

        try:
            raise RuntimeError("test error")
        except RuntimeError:
            import sys
            record.exc_info = sys.exc_info()
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "RuntimeError" in data["exception"]


class TestObservability:
    def test_configure_logging_idempotent(self) -> None:
        """observability.py line 18: early return if handlers exist."""
        logger = logging.getLogger("rag_pipeline")
        initial_count = len(logger.handlers)
        configure_logging()
        configure_logging()
        assert len(logger.handlers) <= initial_count + 1


class TestRetrieverEdgeCases:
    def test_search_empty_query_returns_empty(self) -> None:
        """retrieval.py line 28: empty query."""
        from rag_pipeline.chunking import Chunk
        retriever = Retriever()
        chunks = [Chunk(doc_id="d1", text="hello world", start_char=0, end_char=11)]
        retriever.fit(chunks)
        result = retriever.search(chunks, "   ", top_k=3)
        assert result == []

    def test_search_no_matrix_returns_empty(self) -> None:
        """retrieval.py line 28: no matrix."""
        from rag_pipeline.chunking import Chunk
        retriever = Retriever()
        chunks = [Chunk(doc_id="d1", text="hello", start_char=0, end_char=5)]
        result = retriever.search(chunks, "hello", top_k=3)
        assert result == []


class TestSecurityRequireRole:
    def test_require_role_raises_on_mismatch(self) -> None:
        """security.py lines 51, 53-54."""
        ctx = AuthContext(subject="test", role="user")
        with pytest.raises(HTTPException) as exc_info:
            AuthManager.require_role(ctx, "admin")
        assert exc_info.value.status_code == 403
        assert "requires role=admin" in exc_info.value.detail

    def test_require_role_passes_on_match(self) -> None:
        ctx = AuthContext(subject="admin", role="admin")
        AuthManager.require_role(ctx, "admin")


class TestRateLimiter:
    def test_rate_limiter_allows_within_limit(self) -> None:
        limiter = InMemoryRateLimiter(limit=5, window_seconds=60)
        for _ in range(5):
            limiter.check("user1")

    def test_rate_limiter_blocks_over_limit(self) -> None:
        """security.py line 31: rate limit exceeded."""
        limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
        limiter.check("user1")
        limiter.check("user1")
        with pytest.raises(HTTPException) as exc_info:
            limiter.check("user1")
        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in exc_info.value.detail


class TestAuthManagerInvalidToken:
    def test_invalid_token_raises_401(self) -> None:
        """security.py: invalid token path."""
        provider = AuthManager()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer invalid-token-xyz"
        with pytest.raises(HTTPException) as exc_info:
            provider.authenticate(mock_request)
        assert exc_info.value.status_code == 401

    def test_missing_bearer_raises_401(self) -> None:
        provider = AuthManager()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        with pytest.raises(HTTPException) as exc_info:
            provider.authenticate(mock_request)
        assert exc_info.value.status_code == 401
        assert "missing bearer token" in exc_info.value.detail


class TestLoadPdfDocument:
    def test_load_blank_pdf_raises(self, tmp_path: Path) -> None:
        """documents.py lines 30-31: PDF loading path with empty text."""
        try:
            from pypdf import PdfWriter
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            pdf_path = tmp_path / "blank.pdf"
            with pdf_path.open("wb") as fh:
                writer.write(fh)
            with pytest.raises(ValueError, match="no extractable text"):
                load_document(pdf_path)
        except ImportError:
            pytest.skip("pypdf not installed")
