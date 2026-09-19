"""Metrics for evaluating SentinelOps investigation decisions."""

from __future__ import annotations

from collections.abc import Sequence
import re


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


def _tokens(text: str) -> set[str]:
    """Normalize text into simple comparable tokens."""
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2
    }


def concept_coverage(
    evidence_texts: Sequence[str],
    concept_groups: Sequence[Sequence[str]],
) -> float:
    """Measure coverage of semantic evidence concepts.

    Each concept group represents one required idea. A group is matched when
    at least one of its phrases has meaningful token overlap with the evidence.
    This avoids requiring synthetic telemetry to reproduce public-report prose.
    """
    if not concept_groups:
        return 1.0

    corpus_tokens = _tokens(" ".join(evidence_texts))
    matched = 0
    for group in concept_groups:
        group_matched = False
        for phrase in group:
            phrase_tokens = _tokens(phrase)
            if phrase_tokens and phrase_tokens <= corpus_tokens:
                group_matched = True
                break
            if phrase_tokens:
                overlap = len(phrase_tokens & corpus_tokens) / len(phrase_tokens)
                if overlap >= 0.5:
                    group_matched = True
                    break
        matched += int(group_matched)
    return matched / len(concept_groups)


def text_concept_match(text: str, concept_groups: Sequence[Sequence[str]]) -> float:
    """Score how much of an expected causal description is represented in text."""
    return concept_coverage([text], concept_groups)


def recovery_action_concept_match(
    recovery_actions: Sequence[str],
    concept_groups: Sequence[Sequence[str]],
) -> float:
    """Measure recovery intent coverage without requiring exact wording."""
    return concept_coverage(recovery_actions, concept_groups)


def evidence_term_coverage(
    evidence_texts: Sequence[str],
    required_terms: Sequence[str],
) -> float:
    """Backward-compatible exact-term coverage metric."""
    if not required_terms:
        return 1.0
    corpus = " ".join(evidence_texts).lower()
    matched = sum(term.lower() in corpus for term in required_terms)
    return matched / len(required_terms)


def recovery_action_contains(
    recovery_actions: Sequence[str],
    required_phrase: str,
) -> float:
    """Backward-compatible exact recovery phrase check."""
    if not recovery_actions:
        return 0.0
    phrase = required_phrase.lower()
    return 1.0 if any(phrase in action.lower() for action in recovery_actions) else 0.0
