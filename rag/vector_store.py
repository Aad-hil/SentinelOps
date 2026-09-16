"""Qdrant vector storage for SentinelOps document chunks."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient, models

from rag.chunking import DocumentChunk

DEFAULT_COLLECTION = "sentinelops_knowledge"


def stable_point_id(chunk_id: str) -> str:
    """Return a deterministic UUID-like identifier accepted by Qdrant."""
    digest = hashlib.md5(chunk_id.encode("utf-8"), usedforsecurity=False).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-5{digest[13:16]}-"
        f"{8 + (int(digest[16], 16) % 4):x}{digest[17:20]}-{digest[20:32]}"
    )


class QdrantVectorStore:
    """Store and search embedded knowledge chunks in Qdrant."""

    def __init__(
        self,
        *,
        url: str = "http://localhost:6333",
        collection_name: str = DEFAULT_COLLECTION,
        dimension: int = 1024,
        client: QdrantClient | None = None,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be greater than zero")
        if not collection_name:
            raise ValueError("collection_name cannot be empty")

        self.collection_name = collection_name
        self.dimension = dimension
        self.client = client or QdrantClient(url=url)

    def ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        if self.client.collection_exists(collection_name=self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.dimension,
                distance=models.Distance.COSINE,
            ),
        )

    def upsert_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        """Upsert chunks and their embeddings, returning the point count."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        for embedding in embeddings:
            if len(embedding) != self.dimension:
                raise ValueError(
                    f"Expected {self.dimension} dimensions, got {len(embedding)}"
                )

        self.ensure_collection()
        points = [
            models.PointStruct(
                id=stable_point_id(chunk.chunk_id),
                vector=list(embedding),
                payload={
                    "content": chunk.content,
                    "source": chunk.source,
                    "category": chunk.category,
                    "chunk_id": chunk.chunk_id,
                    **chunk.metadata,
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
        return len(points)

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        limit: int = 5,
    ) -> list[Any]:
        """Search the collection using cosine similarity."""
        if len(query_embedding) != self.dimension:
            raise ValueError(
                f"Expected {self.dimension} dimensions, got {len(query_embedding)}"
            )
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        return self.client.query_points(
            collection_name=self.collection_name,
            query=list(query_embedding),
            limit=limit,
        ).points
