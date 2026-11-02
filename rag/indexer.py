"""Knowledge-corpus indexing pipeline for SentinelOps."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from rag.chunking import DocumentChunk, chunk_documents
from rag.embeddings import EmbeddingProvider, create_embedding_provider_from_env
from rag.ingestion import load_markdown_documents
from rag.models import Document
from rag.vector_store import DEFAULT_COLLECTION, QdrantVectorStore


@dataclass(frozen=True)
class IndexResult:
    """Summary of one knowledge indexing run."""

    documents: int
    chunks: int
    vectors: int
    collection: str


def _normalize_document_sources(
    documents: list[Document],
    knowledge_root: str | Path,
) -> list[Document]:
    """Make stored source paths relative to the knowledge corpus root."""
    root = Path(knowledge_root).resolve()
    normalized: list[Document] = []

    for document in documents:
        source_path = Path(document.source)
        try:
            relative_source = source_path.resolve().relative_to(root).as_posix()
        except ValueError:
            relative_source = document.source.replace("\\", "/")

        normalized.append(
            Document(
                content=document.content,
                source=relative_source,
                category=document.category,
                metadata={
                    **document.metadata,
                    "filename": Path(relative_source).name,
                    "path": relative_source,
                },
            )
        )

    return normalized


def index_knowledge(
    *,
    knowledge_root: str | Path = "knowledge",
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: QdrantVectorStore | None = None,
    chunk_size: int = 900,
    chunk_overlap: int | None = None,
) -> IndexResult:
    """Load, chunk, embed, and store the SentinelOps knowledge corpus."""
    documents = load_markdown_documents(knowledge_root)
    documents = _normalize_document_sources(documents, knowledge_root)
    chunks: list[DocumentChunk] = chunk_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    provider = embedding_provider or create_embedding_provider_from_env()
    store = vector_store or QdrantVectorStore(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        collection_name=os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION),
        dimension=provider.dimension,
    )

    embeddings = provider.embed_documents([chunk.content for chunk in chunks])
    vectors = store.upsert_chunks(chunks, embeddings)

    return IndexResult(
        documents=len(documents),
        chunks=len(chunks),
        vectors=vectors,
        collection=store.collection_name,
    )


def main() -> None:
    """Index the local knowledge corpus into the configured vector store."""
    parser = argparse.ArgumentParser(description="Index SentinelOps knowledge documents.")
    parser.add_argument("--knowledge-root", default="knowledge")
    args = parser.parse_args()
    result = index_knowledge(knowledge_root=args.knowledge_root)
    print(
        f"Indexed {result.documents} documents into {result.chunks} chunks "
        f"({result.vectors} vectors) in collection '{result.collection}'."
    )


if __name__ == "__main__":
    main()
