"""Tests for retrieval evaluation metrics."""

import pytest

from evaluation.retrieval_metrics import (
    mean_reciprocal_rank,
    recall_at_k,
    unique_source_count,
)


def test_recall_at_k_counts_relevant_sources_found() -> None:
    retrieved = ["a.md", "b.md", "b.md", "c.md"]
    assert recall_at_k(retrieved, {"a.md", "c.md"}, 3) == 0.5


def test_recall_at_k_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        recall_at_k(["a.md"], {"a.md"}, 0)
    with pytest.raises(ValueError, match="cannot be empty"):
        recall_at_k(["a.md"], set(), 1)


def test_mean_reciprocal_rank_uses_first_relevant_result() -> None:
    ranked = [
        ["noise.md", "target.md"],
        ["target.md", "noise.md"],
        ["noise.md"],
    ]
    relevant = [{"target.md"}, {"target.md"}, {"target.md"}]
    assert mean_reciprocal_rank(ranked, relevant) == pytest.approx((0.5 + 1.0) / 3)


def test_mean_reciprocal_rank_rejects_mismatched_inputs() -> None:
    with pytest.raises(ValueError, match="equal length"):
        mean_reciprocal_rank([["a.md"]], [])


def test_unique_source_count_ignores_duplicate_chunks() -> None:
    assert unique_source_count(["a.md", "a.md", "b.md", "c.md"], 3) == 2
