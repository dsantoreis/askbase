import argparse
from pathlib import Path

from .pipeline import RAGPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal local RAG pipeline demo")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("paths", nargs="+")
    ingest.add_argument("--index", default="rag_index.pkl")
    ingest.add_argument("--chunk-size", type=int, default=500)
    ingest.add_argument("--overlap", type=int, default=100)

    ask = sub.add_parser("ask")
    ask.add_argument("query")
    ask.add_argument("--index", default="rag_index.pkl")
    ask.add_argument("--top-k", type=int, default=3)

    args = parser.parse_args()

    if args.command == "ingest":
        rag = RAGPipeline()
        count = rag.ingest_paths(args.paths, chunk_size=args.chunk_size, overlap=args.overlap)
        rag.save(args.index)
        print(f"Indexed {count} chunks into {args.index}")
    else:
        index = Path(args.index)
        if not index.exists():
            raise SystemExit(f"Index not found: {index}. Run ingest first.")
        rag = RAGPipeline.load(index)
        print(rag.answer(args.query, top_k=args.top_k))


if __name__ == "__main__":
    main()
