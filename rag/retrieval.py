"""Baseline semantic retrieval for the SentinelOps knowledge corpus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rag.embeddings import BedrockEmbeddingProvider, EmbeddingProvider
from rag.vector_store import DEFAULT_COLLECTION, QdrantVectorStore


@dataclass(frozen=True)
class RetrievalResult:
    """One knowledge chunk returned by semantic retrieval."""

    content: str
    source: str
    category: str
    chunk_id: str
    score: float
    metadata: dict[str, Any]


class KnowledgeRetriever:
    """Embed a query and retrieve the most similar chunks from Qdrant."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or BedrockEmbeddingProvider()
        self.vector_store = vector_store or QdrantVectorStore(
            collection_name=DEFAULT_COLLECTION,
            dimension=self.embedding_provider.dimension,
        )

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        """Return the top-k semantically similar knowledge chunks."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        query_embedding = self.embedding_provider.embed_text(query)
        points = self.vector_store.search(query_embedding, limit=top_k)

        results: list[RetrievalResult] = []
        for point in points:
            payload = getattr(point, "payload", None) or {}
            results.append(
                RetrievalResult(
                    content=str(payload.get("content", "")),
                    source=str(payload.get("source", "")),
                    category=str(payload.get("category", "")),
                    chunk_id=str(payload.get("chunk_id", "")),
                    score=float(getattr(point, "score", 0.0)),
                    metadata={
                        key: value
                        for key, value in payload.items()
                        if key not in {"content", "source", "category", "chunk_id"}
                    },
                )
            )
        return results
