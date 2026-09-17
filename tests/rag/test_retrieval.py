"""Tests for baseline semantic retrieval."""

from dataclasses import dataclass

import pytest

from rag.retrieval import KnowledgeRetriever


class FakeEmbeddingProvider:
    dimension = 3

    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.queries.append(text)
        return [1.0, 0.0, 0.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


@dataclass
class FakePoint:
    score: float
    payload: dict[str, object]


class FakeVectorStore:
    def __init__(self) -> None:
        self.calls: list[tuple[list[float], int]] = []

    def search(self, query_embedding: list[float], *, limit: int) -> list[FakePoint]:
        self.calls.append((query_embedding, limit))
        return [
            FakePoint(
                score=0.91,
                payload={
                    "content": "Check database CPU and query latency.",
                    "source": "runbooks/database-high-cpu.md",
                    "category": "runbook",
                    "chunk_id": "database-high-cpu:0",
                    "path": "runbooks/database-high-cpu.md",
                },
            ),
            FakePoint(
                score=0.72,
                payload={
                    "content": "Review the latest deployment before rollback.",
                    "source": "runbooks/deployment-rollback.md",
                    "category": "runbook",
                    "chunk_id": "deployment-rollback:0",
                    "path": "runbooks/deployment-rollback.md",
                },
            ),
        ]


def test_retrieve_embeds_query_and_returns_ranked_results() -> None:
    provider = FakeEmbeddingProvider()
    store = FakeVectorStore()
    retriever = KnowledgeRetriever(
        embedding_provider=provider,
        vector_store=store,
    )

    results = retriever.retrieve("Why are checkout requests failing?", top_k=2)

    assert provider.queries == ["Why are checkout requests failing?"]
    assert store.calls == [([1.0, 0.0, 0.0], 2)]
    assert [result.score for result in results] == [0.91, 0.72]
    assert results[0].source == "runbooks/database-high-cpu.md"
    assert results[0].metadata == {"path": "runbooks/database-high-cpu.md"}


def test_retrieve_rejects_empty_query() -> None:
    retriever = KnowledgeRetriever(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="non-empty"):
        retriever.retrieve("   ")


def test_retrieve_rejects_invalid_top_k() -> None:
    retriever = KnowledgeRetriever(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore(),
    )

    with pytest.raises(ValueError, match="greater than zero"):
        retriever.retrieve("database issue", top_k=0)
