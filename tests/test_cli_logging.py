from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from rag_pipeline import cli
from rag_pipeline.logging_utils import JsonFormatter, configure_logging


def test_json_formatter_and_configure_logging() -> None:
    configure_logging("debug")
    record = logging.LogRecord(
        name="rag", level=logging.INFO, pathname=__file__, lineno=1, msg="hello", args=(), exc_info=None
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"


def test_cli_ingest_ask_evaluate_and_serve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    doc = tmp_path / "a.txt"
    doc.write_text("MFA is required for admins", encoding="utf-8")
    idx = tmp_path / "idx.pkl"
    ds = tmp_path / "eval.jsonl"
    ds.write_text(json.dumps({"query": "MFA required", "relevant_doc_ids": [str(doc)]}) + "\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["rag", "ingest", str(doc), "--index", str(idx)])
    cli.main()
    assert idx.exists()

    monkeypatch.setattr("sys.argv", ["rag", "ask", "MFA", "--index", str(idx), "--json"])
    cli.main()
    out = capsys.readouterr().out
    assert "citations" in out

    monkeypatch.setattr("sys.argv", ["rag", "evaluate", "--index", str(idx), "--dataset", str(ds)])
    cli.main()
    out_eval = capsys.readouterr().out
    assert "context_precision" in out_eval

    called = {}

    def fake_run(app, host, port):
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr(cli.uvicorn, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["rag", "serve", "--index", str(idx), "--host", "0.0.0.0", "--port", "9999"])
    cli.main()
    assert called == {"host": "0.0.0.0", "port": 9999}


def test_cli_ask_missing_index_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing.pkl"
    monkeypatch.setattr("sys.argv", ["rag", "ask", "hi", "--index", str(missing)])
    with pytest.raises(SystemExit):
        cli.main()


def test_cli_ask_invalid_top_k_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    idx = tmp_path / "idx.pkl"
    idx.write_bytes(b"placeholder")
    monkeypatch.setattr("sys.argv", ["rag", "ask", "hi", "--index", str(idx), "--top-k", "0"])
    with pytest.raises(SystemExit):
        cli.main()


def test_cli_status_reports_index_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    missing = tmp_path / "missing.pkl"
    monkeypatch.setattr("sys.argv", ["rag", "status", "--index", str(missing)])
    cli.main()
    missing_payload = json.loads(capsys.readouterr().out)
    assert missing_payload["index_exists"] is False

    doc = tmp_path / "status.txt"
    doc.write_text("SOC2 logging controls", encoding="utf-8")
    idx = tmp_path / "idx.pkl"
    rag = cli.RAGPipeline()
    rag.ingest([doc])
    rag.save(idx)

    monkeypatch.setattr("sys.argv", ["rag", "status", "--index", str(idx)])
    cli.main()
    present_payload = json.loads(capsys.readouterr().out)
    assert present_payload["index_exists"] is True
    assert present_payload["chunks"] > 0


def test_cli_status_supports_pretty_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    missing = tmp_path / "missing.pkl"
    monkeypatch.setattr("sys.argv", ["rag", "status", "--index", str(missing), "--pretty"])
    cli.main()
    out = capsys.readouterr().out
    assert "\n" in out
    payload = json.loads(out)
    assert payload["index_exists"] is False
