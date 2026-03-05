from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .api import create_app
from .logging_utils import configure_logging
from .pipeline import IngestConfig, RAGPipeline, RetrievalConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Enterprise-ready local RAG pipeline")
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("paths", nargs="+")
    ingest.add_argument("--index", default="rag_index.pkl")
    ingest.add_argument("--chunk-size", type=int, default=500)
    ingest.add_argument("--overlap", type=int, default=100)
    ingest.add_argument("--chunk-strategy", choices=["char", "paragraph"], default="char")
    ingest.add_argument("--max-file-mb", type=int, default=5)
    ingest.add_argument("--min-chars", type=int, default=30)

    ask = sub.add_parser("ask")
    ask.add_argument("query")
    ask.add_argument("--index", default="rag_index.pkl")
    ask.add_argument("--top-k", type=int, default=3)
    ask.add_argument("--json", action="store_true")

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--index", default="rag_index.pkl")
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument("--k", type=int, default=3)

    serve = sub.add_parser("serve")
    serve.add_argument("--index", default="rag_index.pkl")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    args = parser.parse_args()
    configure_logging(args.log_level)

    if args.command == "ingest":
        rag = RAGPipeline(
            ingest_config=IngestConfig(
                chunk_size=args.chunk_size,
                overlap=args.overlap,
                chunk_strategy=args.chunk_strategy,
                max_file_mb=args.max_file_mb,
                min_chars=args.min_chars,
            ),
            retrieval_config=RetrievalConfig(),
        )
        count = rag.ingest_paths(args.paths)
        rag.save(args.index)
        print(f"Indexed {count} chunks into {args.index}")
        return

    if args.command == "ask":
        index = Path(args.index)
        if not index.exists():
            raise SystemExit(f"Index not found: {index}. Run ingest first.")
        rag = RAGPipeline.load(index)
        answer = rag.answer(args.query, top_k=args.top_k)
        if args.json:
            print(json.dumps({"query": args.query, "answer": answer}, ensure_ascii=False))
        else:
            print(answer)
        return

    if args.command == "evaluate":
        index = Path(args.index)
        if not index.exists():
            raise SystemExit(f"Index not found: {index}. Run ingest first.")
        rag = RAGPipeline.load(index)
        report = rag.evaluate_precision_at_k(args.dataset, k=args.k)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.command == "serve":
        app = create_app(index_path=args.index)
        uvicorn.run(app, host=args.host, port=args.port)
        return


if __name__ == "__main__":
    main()
