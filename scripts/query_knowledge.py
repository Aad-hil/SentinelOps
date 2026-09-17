"""CLI for testing baseline semantic retrieval against Qdrant."""

from __future__ import annotations

import argparse

from rag.retrieval import KnowledgeRetriever


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the SentinelOps knowledge base")
    parser.add_argument("query", help="Natural-language incident investigation query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to return")
    args = parser.parse_args()

    retriever = KnowledgeRetriever()
    results = retriever.retrieve(args.query, top_k=args.top_k)

    if not results:
        print("No matching knowledge chunks found.")
        return

    for rank, result in enumerate(results, start=1):
        print(f"[{rank}] score={result.score:.4f} | {result.source}")
        print(f"    category: {result.category}")
        print(f"    chunk_id: {result.chunk_id}")
        print(f"    {result.content[:500]}")
        print()


if __name__ == "__main__":
    main()
