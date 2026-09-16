"""Knowledge-corpus indexing pipeline for SentinelOps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rag.chunking import DocumentChunk, chunk_documents
from rag.embeddings import BedrockEmbeddingProvider, EmbeddingProvider
from rag.ingestion import load_markdown_documents
from rag.vector_store import DEFAULT_COLLECTION, QdrantVectorStore


@dataclass(frozen=True)
class IndexResult:
    """Summary of one knowledge indexing run."""

    documents: int
    chunks: int
    vectors: int
    collection: str


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
    chunks: list[DocumentChunk] = chunk_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    provider = embedding_provider or BedrockEmbeddingProvider()
    store = vector_store or QdrantVectorStore(
        collection_name=DEFAULT_COLLECTION,
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
