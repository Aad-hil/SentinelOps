"""CLI entry point for indexing the SentinelOps knowledge corpus."""

from rag.indexer import index_knowledge


def main() -> None:
    result = index_knowledge()
    print(f"Indexed {result.documents} documents into {result.chunks} chunks.")
    print(f"Stored {result.vectors} vectors in '{result.collection}'.")


if __name__ == "__main__":
    main()
