from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
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
    serve.add_argument("--seed", action="store_true", help="Auto-ingest data/seed/ on first run if no index exists")

    status = sub.add_parser("status")
    status.add_argument("--index", default="artifacts/rag_index.pkl")
    status.add_argument("--pretty", action="store_true")

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
        if args.seed and not Path(args.index).exists():
            seed_dir = Path(__file__).resolve().parent.parent.parent / "data" / "seed"
            if seed_dir.is_dir():
                rag = RAGPipeline()
                chunks = rag.ingest([str(seed_dir)])
                rag.save(args.index)
                print(f"Seed mode: indexed {chunks} chunks from {seed_dir}")
        uvicorn.run(create_app(index_path=args.index), host=args.host, port=args.port)
        return

    if args.command == "status":
        index_path = Path(args.index)
        generated_at_utc = datetime.now(timezone.utc).isoformat()

        if not index_path.exists():
            payload = {
                "index_exists": False,
                "index_path": str(index_path),
                "chunks": 0,
                "generated_at_utc": generated_at_utc,
            }
            print(json.dumps(payload, indent=2 if args.pretty else None))
            return

        rag = RAGPipeline.load(index_path)
        payload = {
            "index_exists": True,
            "index_path": str(index_path),
            "chunks": len(rag.chunks),
            "chunk_size": rag.chunk_size,
            "overlap": rag.overlap,
            "generated_at_utc": generated_at_utc,
        }
        print(json.dumps(payload, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
