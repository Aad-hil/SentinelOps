import pytest

from safety.approval import record_human_approval
from safety.models import SafetyDecision


def state():
    return {"safety_decision": SafetyDecision(
        decision="review_required",
        rationale="Human review required.",
        risk_level="medium",
        approval_required=True,
    )}


def test_human_approval_is_recorded_without_execution():
    result = record_human_approval(state(), approved=True, reviewer="operator-1")
    assert result["approval_status"] == "approved"
    assert result["approval_required"] is False
    assert result["investigation_status"] == "approved_for_execution"


def test_human_rejection_blocks_recovery():
    result = record_human_approval(state(), approved=False, reviewer="operator-1")
    assert result["approval_status"] == "rejected"
    assert result["investigation_status"] == "blocked"


def test_human_approval_requires_reviewer():
    with pytest.raises(ValueError, match="reviewer"):
        record_human_approval(state(), approved=True, reviewer=" ")


def test_human_approval_requires_safety_decision():
    with pytest.raises(ValueError, match="safety decision"):
        record_human_approval({}, approved=True, reviewer="operator-1")
