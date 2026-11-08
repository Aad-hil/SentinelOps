"""Safety boundaries must remain intact for blocked and reviewable plans."""
from recovery.models import RecoveryPlan, RecoveryStep
from safety.policy import evaluate_recovery_safety


def _plan(*, confidence=0.9, readiness="ready_for_review", risk="medium"):
    return RecoveryPlan(
        incident_id="RS-001", hypothesis_id="RSH1", confidence=confidence,
        readiness=readiness, rationale="Controlled test evidence.",
        steps=(RecoveryStep(
            step_id="review-wlm", action="Prepare reversible WLM adjustment for review.",
            purpose="Review only; never execute automatically.", risk=risk,
            requires_approval=True,
        ),),
    )


def test_supported_medium_risk_plan_requires_human_review():
    decision = evaluate_recovery_safety(_plan())
    assert decision.decision == "review_required"
    assert decision.human_approval_required


def test_insufficient_evidence_blocks_remediation():
    decision = evaluate_recovery_safety(_plan(confidence=0.70, readiness="verification_required"))
    assert decision.decision == "blocked"
    assert not decision.human_approval_required


def test_evidence_gaps_are_deduplicated():
    plan = RecoveryPlan(
        incident_id="RS-001", hypothesis_id="RSH1", confidence=0.5,
        readiness="verification_required", rationale="Missing evidence",
        steps=tuple(RecoveryStep(
            step_id=f"step-{i}", action="Inspect logs", purpose="Diagnose",
            risk="low", requires_approval=False, evidence=("duplicate-ref",)
        ) for i in range(3)),
    )
    decision = evaluate_recovery_safety(plan)
    assert decision.evidence_gaps.count("duplicate-ref") == 1
