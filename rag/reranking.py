"""Local cross-encoder reranking and source diversification for retrieval."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Protocol

from rag.retrieval import RetrievalResult

DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
DEFAULT_MAX_RESULTS_PER_SOURCE = 2


class Reranker(Protocol):
    """Interface implemented by SentinelOps reranking backends."""

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """Return one relevance score for each document."""


class LocalCrossEncoderReranker:
    """Rerank retrieved passages with a local Sentence Transformers model.

    The model is downloaded and cached locally on first use. No external
    inference API is called during reranking.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_RERANKER_MODEL,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        if not model_name and model is None:
            raise ValueError("model_name cannot be empty when model is not provided")
        if model is None:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(
                model_name,
                max_length=512,
                device=device,
            )
        self.model_name = model_name
        self.model = model

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        """Score query/document pairs in input order."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not documents:
            return []
        if any(
            not isinstance(document, str) or not document.strip()
            for document in documents
        ):
            raise ValueError("documents must contain only non-empty strings")

        pairs = [(query, document) for document in documents]
        scores = self.model.predict(pairs, show_progress_bar=False)
        return [float(score) for score in scores]


def rerank_results(
    query: str,
    results: Sequence[RetrievalResult],
    reranker: Reranker,
    *,
    top_k: int = 5,
) -> list[RetrievalResult]:
    """Rerank retrieval candidates and return the highest-scoring results."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if not results:
        return []

    scores = reranker.score(query, [result.content for result in results])
    if len(scores) != len(results):
        raise ValueError("reranker must return one score per result")

    ranked = [
        (score, result)
        for score, result in zip(scores, results, strict=True)
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)

    reranked: list[RetrievalResult] = []
    for score, result in ranked[:top_k]:
        metadata = {**result.metadata, "rerank_score": score}
        reranked.append(
            RetrievalResult(
                content=result.content,
                source=result.source,
                category=result.category,
                chunk_id=result.chunk_id,
                score=score,
                metadata=metadata,
            )
        )
    return reranked


def diversify_results(
    results: Sequence[RetrievalResult],
    *,
    top_k: int = 5,
    max_per_source: int = DEFAULT_MAX_RESULTS_PER_SOURCE,
) -> list[RetrievalResult]:
    """Limit repeated chunks from one source while preserving reranker order.

    Results are considered in their existing relevance order. The first
    ``max_per_source`` chunks from each source are retained, then a second
    pass fills any remaining slots with skipped results. The second pass
    prevents diversification from returning fewer than ``top_k`` results
    when the candidate set contains too few distinct sources.
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")
    if max_per_source <= 0:
        raise ValueError("max_per_source must be greater than zero")
    if not results:
        return []

    selected: list[RetrievalResult] = []
    skipped: list[RetrievalResult] = []
    source_counts: dict[str, int] = defaultdict(int)

    for result in results:
        if source_counts[result.source] < max_per_source:
            selected.append(result)
            source_counts[result.source] += 1
            if len(selected) == top_k:
                break
        else:
            skipped.append(result)

    if len(selected) < top_k:
        selected.extend(skipped[: top_k - len(selected)])

    return selected[:top_k]
