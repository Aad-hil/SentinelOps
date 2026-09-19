"""Metrics for evaluating SentinelOps investigation decisions."""

from __future__ import annotations

from collections.abc import Sequence


def top1_hypothesis_accuracy(predicted_ids: Sequence[str], expected_id: str) -> float:
    """Return 1 when the first predicted hypothesis matches the expected ID."""
    if not predicted_ids:
        return 0.0
    return 1.0 if predicted_ids[0] == expected_id else 0.0


def top_k_hypothesis_recall(
    predicted_ids: Sequence[str],
    expected_id: str,
    k: int,
) -> float:
    """Return 1 when the expected hypothesis appears within the top-k."""
    if k <= 0:
        raise ValueError("k must be greater than zero")
    return 1.0 if expected_id in predicted_ids[:k] else 0.0


def confidence_brier_score(
    predicted_ids: Sequence[str],
    confidence_by_id: dict[str, float],
    expected_id: str,
) -> float:
    """Score confidence assigned to the expected hypothesis using Brier loss."""
    if not predicted_ids:
        return 1.0
    probability = confidence_by_id.get(expected_id, 0.0)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("confidence values must be between zero and one")
    return (probability - 1.0) ** 2


def evidence_term_coverage(
    evidence_texts: Sequence[str],
    required_terms: Sequence[str],
) -> float:
    """Return the fraction of required evidence statements represented in evidence."""
    if not required_terms:
        return 1.0
    corpus = " ".join(evidence_texts).lower()
    matched = sum(term.lower() in corpus for term in required_terms)
    return matched / len(required_terms)


def recovery_action_contains(
    recovery_actions: Sequence[str],
    required_phrase: str,
) -> float:
    """Return 1 when at least one proposed recovery action contains the phrase."""
    if not recovery_actions:
        return 0.0
    phrase = required_phrase.lower()
    return 1.0 if any(phrase in action.lower() for action in recovery_actions) else 0.0
