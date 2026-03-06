from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .api import create_app
from .evaluation import evaluate_context_precision
from .pipeline import RAGPipeline, citations_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio-grade local RAG pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("paths", nargs="+")
    ingest.add_argument("--index", default="artifacts/rag_index.pkl")
    ingest.add_argument("--chunk-size", type=int, default=220)
    ingest.add_argument("--overlap", type=int, default=40)

    ask = sub.add_parser("ask")
    ask.add_argument("query")
    ask.add_argument("--index", default="artifacts/rag_index.pkl")
    ask.add_argument("--top-k", type=int, default=3)
    ask.add_argument("--json", action="store_true")

    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--index", default="artifacts/rag_index.pkl")
    evaluate.add_argument("--dataset", required=True)
    evaluate.add_argument("--k", type=int, default=3)

    serve = sub.add_parser("serve")
    serve.add_argument("--index", default="artifacts/rag_index.pkl")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    status = sub.add_parser("status")
    status.add_argument("--index", default="artifacts/rag_index.pkl")

    args = parser.parse_args()

    if args.command == "ingest":
        rag = RAGPipeline(chunk_size=args.chunk_size, overlap=args.overlap)
        chunks = rag.ingest(args.paths)
        rag.save(args.index)
        print(f"Indexed {chunks} chunks into {args.index}")
        return

    if args.command == "ask":
        if args.top_k <= 0:
            raise SystemExit("--top-k must be >= 1")

        index_path = Path(args.index)
        if not index_path.exists():
            raise SystemExit(f"index not found: {index_path}")
        rag = RAGPipeline.load(index_path)
        result = rag.ask(args.query, top_k=args.top_k)
        if args.json:
            print(json.dumps({"answer": result.text, "citations": citations_to_dict(result.citations)}))
        else:
            print(result.text)
        return

    if args.command == "evaluate":
        report = evaluate_context_precision(args.index, args.dataset, k=args.k)
        print(json.dumps(report, indent=2))
        return

    if args.command == "serve":
        uvicorn.run(create_app(index_path=args.index), host=args.host, port=args.port)
        return

    if args.command == "status":
        index_path = Path(args.index)
        if not index_path.exists():
            print(json.dumps({"index_exists": False, "index_path": str(index_path), "chunks": 0}))
            return

        rag = RAGPipeline.load(index_path)
        print(
            json.dumps(
                {
                    "index_exists": True,
                    "index_path": str(index_path),
                    "chunks": len(rag.chunks),
                    "chunk_size": rag.chunk_size,
                    "overlap": rag.overlap,
                }
            )
        )


if __name__ == "__main__":
    main()
