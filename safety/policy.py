from recovery.models import RecoveryPlan
from safety.models import SafetyDecision


def evaluate_recovery_safety(plan: RecoveryPlan | None) -> SafetyDecision:
    """Apply deterministic guardrails; never execute or approve production changes."""
    if plan is None:
        return SafetyDecision(
            decision="blocked",
            rationale="No recovery plan is available for safety review.",
            risk_level="high",
            approval_required=False,
        )

    if plan.readiness in {"blocked", "verification_required"}:
        gaps = tuple(
            evidence
            for step in plan.steps
            for evidence in step.evidence
        )
        return SafetyDecision(
            decision="blocked",
            rationale=(
                "Recovery remains blocked until the investigation resolves its evidence "
                "gaps; production-changing actions must not proceed."
            ),
            risk_level="high" if plan.readiness == "blocked" else "medium",
            approval_required=False,
            blocked_steps=tuple(step.step_id for step in plan.steps if step.requires_approval),
            reviewed_steps=tuple(step.step_id for step in plan.steps if not step.requires_approval),
            evidence_gaps=gaps,
        )

    blocked = tuple(
        step.step_id
        for step in plan.steps
        if step.requires_approval and step.risk == "high"
    )
    reviewed = tuple(step.step_id for step in plan.steps if step.step_id not in blocked)
    approval_required = plan.requires_approval

    if blocked:
        return SafetyDecision(
            decision="blocked",
            rationale="High-risk production-changing steps require a dedicated safety review before human approval.",
            risk_level="high",
            approval_required=False,
            blocked_steps=blocked,
            reviewed_steps=reviewed,
        )

    risk_levels = {step.risk for step in plan.steps}
    risk_level = "medium" if "medium" in risk_levels else "low"
    if approval_required:
        return SafetyDecision(
            decision="review_required",
            rationale=(
                "The recovery plan is supported by the investigation, but production-changing "
                "steps require explicit human approval. SentinelOps will not execute them."
            ),
            risk_level=risk_level,
            approval_required=True,
            reviewed_steps=tuple(step.step_id for step in plan.steps),
        )

    return SafetyDecision(
        decision="no_approval_needed",
        rationale="The recovery plan contains no production-changing steps requiring approval.",
        risk_level=risk_level,
        approval_required=False,
        reviewed_steps=tuple(step.step_id for step in plan.steps),
    )
