from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import RAGPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal local RAG pipeline demo")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest files/directories and build index")
    ingest.add_argument("paths", nargs="+", help="Files or directories (.txt/.md)")
    ingest.add_argument("--index", default="rag_index.pkl", help="Index path")
    ingest.add_argument("--chunk-size", type=int, default=500)
    ingest.add_argument("--overlap", type=int, default=100)

    ask = sub.add_parser("ask", help="Ask question against built index")
    ask.add_argument("query", help="Question text")
    ask.add_argument("--index", default="rag_index.pkl", help="Index path")
    ask.add_argument("--top-k", type=int, default=3)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ingest":
        rag = RAGPipeline()
        count = rag.ingest_paths(args.paths, chunk_size=args.chunk_size, overlap=args.overlap)
        rag.save(args.index)
        print(f"Indexed {count} chunks into {args.index}")
        return

    if args.command == "ask":
        index = Path(args.index)
        if not index.exists():
            raise SystemExit(f"Index not found: {index}. Run ingest first.")
        rag = RAGPipeline.load(index)
        print(rag.answer(args.query, top_k=args.top_k))
        return


if __name__ == "__main__":
    main()
