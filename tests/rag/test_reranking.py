"""Tests for local cross-encoder reranking and diversification."""

from dataclasses import dataclass

import pytest

from rag.reranking import (
    LocalCrossEncoderReranker,
    diversify_results,
    rerank_results,
)
from rag.retrieval import RetrievalResult


@dataclass
class FakeModel:
    scores: list[float]

    def predict(self, pairs: list[tuple[str, str]], *, show_progress_bar: bool) -> list[float]:
        assert show_progress_bar is False
        assert len(pairs) == len(self.scores)
        return self.scores


class FakeReranker:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.queries: list[tuple[str, list[str]]] = []

    def score(self, query: str, documents: list[str]) -> list[float]:
        self.queries.append((query, documents))
        return self.scores


def result(source: str, content: str, chunk_id: str = "0") -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="runbook",
        chunk_id=f"{source}:{chunk_id}",
        score=0.5,
        metadata={"path": source},
    )


def test_local_cross_encoder_scores_documents() -> None:
    reranker = LocalCrossEncoderReranker(
        model_name="fake-model",
        model=FakeModel(scores=[0.2, 0.9]),
    )

    assert reranker.score("database issue", ["first", "second"]) == [0.2, 0.9]


def test_rerank_results_sorts_by_cross_encoder_score() -> None:
    candidates = [
        result("a.md", "low relevance"),
        result("b.md", "high relevance"),
        result("c.md", "medium relevance"),
    ]
    reranker = FakeReranker([0.2, 0.9, 0.6])

    ranked = rerank_results(
        "database issue",
        candidates,
        reranker,
        top_k=2,
    )

    assert [item.source for item in ranked] == ["b.md", "c.md"]
    assert [item.score for item in ranked] == [0.9, 0.6]
    assert ranked[0].metadata["rerank_score"] == 0.9
    assert reranker.queries == [
        ("database issue", ["low relevance", "high relevance", "medium relevance"])
    ]


def test_diversify_results_strictly_limits_repeated_sources() -> None:
    candidates = [
        result("a.md", "a1", "1"),
        result("a.md", "a2", "2"),
        result("a.md", "a3", "3"),
        result("b.md", "b1", "1"),
        result("c.md", "c1", "1"),
    ]

    diversified = diversify_results(candidates, top_k=4, max_per_source=1)

    assert [item.source for item in diversified] == ["a.md", "b.md", "c.md"]
    assert max(item.source for item in diversified) == "c.md"
    assert len({item.source for item in diversified}) == len(diversified)


def test_diversify_results_returns_fewer_than_top_k_when_limit_requires_it() -> None:
    candidates = [
        result("a.md", "a1", "1"),
        result("a.md", "a2", "2"),
        result("a.md", "a3", "3"),
    ]

    diversified = diversify_results(candidates, top_k=5, max_per_source=2)

    assert [item.source for item in diversified] == ["a.md", "a.md"]
    assert len(diversified) == 2


def test_diversify_results_keeps_two_chunks_per_source_by_default() -> None:
    candidates = [
        result("a.md", "a1", "1"),
        result("a.md", "a2", "2"),
        result("a.md", "a3", "3"),
        result("b.md", "b1", "1"),
        result("c.md", "c1", "1"),
    ]

    diversified = diversify_results(candidates, top_k=5)

    assert [item.source for item in diversified] == [
        "a.md",
        "a.md",
        "b.md",
        "c.md",
    ]
    assert sum(item.source == "a.md" for item in diversified) == 2


def test_diversify_results_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        diversify_results([], top_k=0)

    with pytest.raises(ValueError, match="greater than zero"):
        diversify_results([], max_per_source=0)


def test_rerank_results_rejects_invalid_inputs() -> None:
    reranker = FakeReranker([])

    with pytest.raises(ValueError, match="non-empty"):
        rerank_results("   ", [], reranker)

    with pytest.raises(ValueError, match="greater than zero"):
        rerank_results("query", [], reranker, top_k=0)


def test_local_cross_encoder_rejects_invalid_documents() -> None:
    reranker = LocalCrossEncoderReranker(
        model_name="fake-model",
        model=FakeModel(scores=[0.2]),
    )

    with pytest.raises(ValueError, match="non-empty"):
        reranker.score("query", ["   "])


def test_rerank_results_rejects_wrong_score_count() -> None:
    reranker = FakeReranker([0.9])
    candidates = [result("a.md", "first"), result("b.md", "second")]

    with pytest.raises(ValueError, match="one score per result"):
        rerank_results("query", candidates, reranker)
