from types import SimpleNamespace

from agents.safety import run_safety_agent
from recovery.models import RecoveryPlan, RecoveryStep
from safety.policy import evaluate_recovery_safety


def ready_plan():
    return RecoveryPlan(
        incident_id="INC-002",
        hypothesis_id="H1",
        confidence=0.95,
        readiness="ready_for_review",
        rationale="Supported root cause.",
        steps=(
            RecoveryStep("mitigate", "Rollback deployment", "Reduce impact", "medium", True),
            RecoveryStep("verify", "Verify health", "Confirm recovery", "low", False),
        ),
    )


def test_safety_requires_human_approval_for_production_change():
    decision = evaluate_recovery_safety(ready_plan())
    assert decision.decision == "review_required"
    assert decision.approval_required is True
    assert decision.human_approval_required is True
    assert decision.risk_level == "medium"
    assert decision.blocked_steps == ()


def test_safety_blocks_unvalidated_recovery():
    plan = RecoveryPlan(
        incident_id="INC-001",
        hypothesis_id="H1",
        confidence=0.55,
        readiness="verification_required",
        rationale="Evidence is incomplete.",
        steps=(RecoveryStep("prepare", "Prepare mitigation", "Reduce impact", "medium", True),),
    )
    decision = evaluate_recovery_safety(plan)
    assert decision.decision == "blocked"
    assert decision.approval_required is False
    assert decision.blocked_steps == ("prepare",)


def test_safety_blocks_missing_plan():
    decision = evaluate_recovery_safety(None)
    assert decision.decision == "blocked"
    assert decision.risk_level == "high"


def test_safety_agent_publishes_pending_approval():
    result = run_safety_agent({"recovery_plan": ready_plan()})
    assert result["safety_decision"].decision == "review_required"
    assert result["approval_required"] is True
    assert result["approval_status"] == "pending"
    assert result["investigation_status"] == "awaiting_human_approval"
    assert result["completed_tasks"] == ["safety"]
