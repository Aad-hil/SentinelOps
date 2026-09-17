"""Metrics for evaluating ranked SentinelOps retrieval results."""

from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(
    retrieved_sources: Sequence[str],
    relevant_sources: set[str],
    k: int,
) -> float:
    """Return the fraction of known relevant sources found in the top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero")
    if not relevant_sources:
        raise ValueError("relevant_sources cannot be empty")
    retrieved = set(retrieved_sources[:k])
    return len(retrieved & relevant_sources) / len(relevant_sources)


def mean_reciprocal_rank(
    ranked_sources: Sequence[Sequence[str]],
    relevant_sources: Sequence[set[str]],
) -> float:
    """Return mean reciprocal rank across multiple evaluated queries."""
    if len(ranked_sources) != len(relevant_sources):
        raise ValueError("ranked_sources and relevant_sources must have equal length")
    if not ranked_sources:
        return 0.0

    reciprocal_ranks: list[float] = []
    for results, relevant in zip(ranked_sources, relevant_sources, strict=True):
        if not relevant:
            raise ValueError("each relevant source set must be non-empty")
        reciprocal_rank = 0.0
        for rank, source in enumerate(results, start=1):
            if source in relevant:
                reciprocal_rank = 1.0 / rank
                break
        reciprocal_ranks.append(reciprocal_rank)
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def unique_source_count(retrieved_sources: Sequence[str], k: int) -> int:
    """Count unique source documents in the top-k results."""
    if k <= 0:
        raise ValueError("k must be greater than zero")
    return len(set(retrieved_sources[:k]))
