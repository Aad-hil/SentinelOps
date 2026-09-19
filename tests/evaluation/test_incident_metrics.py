"""Tests for incident-level evaluation metrics."""

import pytest

from evaluation.incident_metrics import (
    confidence_brier_score,
    evidence_term_coverage,
    recovery_action_contains,
    recovery_action_concept_match,
    top1_hypothesis_accuracy,
    top_k_hypothesis_recall,
)


def test_top1_hypothesis_accuracy():
    assert top1_hypothesis_accuracy(["H1", "H2"], "H1") == 1.0
    assert top1_hypothesis_accuracy(["H2", "H1"], "H1") == 0.0
    assert top1_hypothesis_accuracy([], "H1") == 0.0


def test_top_k_hypothesis_recall():
    assert top_k_hypothesis_recall(["H2", "H1"], "H1", 2) == 1.0
    assert top_k_hypothesis_recall(["H2", "H3"], "H1", 2) == 0.0
    with pytest.raises(ValueError, match="greater than zero"):
        top_k_hypothesis_recall(["H1"], "H1", 0)


def test_confidence_brier_score():
    assert confidence_brier_score(["H1"], {"H1": 1.0}, "H1") == 0.0
    assert confidence_brier_score(["H2"], {"H1": 0.0}, "H1") == 1.0
    with pytest.raises(ValueError, match="between zero and one"):
        confidence_brier_score(["H1"], {"H1": 1.2}, "H1")


def test_evidence_term_coverage():
    evidence = [
        "Deployment introduced the problematic query.",
        "Database saturation caused elevated request failures.",
    ]
    required = [
        "deployment introduced the problematic query",
        "database saturation caused elevated request failures",
        "missing evidence",
    ]
    assert evidence_term_coverage(evidence, required) == pytest.approx(2 / 3)


def test_recovery_action_contains():
    assert recovery_action_contains(
        ["Identify query and rollback the deployment."],
        "rollback the deployment",
    ) == 1.0
    assert recovery_action_contains(["verify recovery"], "rollback") == 0.0


def test_recovery_action_concept_match_handles_single_concept_group():
    actions = ["Roll back the data-store to the previous stable version."]
    assert recovery_action_concept_match(actions, (("rollback", "stable"),)) == 1.0
