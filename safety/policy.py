from recovery.models import RecoveryPlan, RecoveryStep
from safety.models import SafetyDecision


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

_HIGH_RISK_ACTION_TERMS = (
    "delete",
    "drop ",
    "truncate",
    "destroy",
    "purge",
    "erase",
    "data migration",
    "database modification",
    "database write",
    "irreversible",
    "disable authentication",
    "disable security",
)

_MEDIUM_RISK_ACTION_TERMS = (
    "rollback",
    "restart",
    "mitigation",
    "mitigate",
    "configuration change",
    "config change",
    "production rollout",
    "production change",
    "deploy",
    "scale",
    "failover",
)


def classify_action_risk(step: RecoveryStep) -> str:
    """Classify an action conservatively, using the declared risk as a minimum."""
    action = step.action.strip().lower()
    if any(term in action for term in _HIGH_RISK_ACTION_TERMS):
        inferred = "high"
    elif any(term in action for term in _MEDIUM_RISK_ACTION_TERMS):
        inferred = "medium"
    elif any(term in action for term in ("collect", "inspect", "verify", "document", "observe", "prepare")):
        inferred = "low"
    else:
        # Unknown production actions fail closed rather than being treated as safe.
        inferred = "high"

    declared = step.risk if step.risk in _RISK_ORDER else "high"
    return inferred if _RISK_ORDER[inferred] > _RISK_ORDER[declared] else declared


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

    effective_risks = {
        step.step_id: classify_action_risk(step)
        for step in plan.steps
    }
    blocked = tuple(
        step.step_id
        for step in plan.steps
        if effective_risks[step.step_id] == "high"
    )
    reviewed = tuple(step.step_id for step in plan.steps if step.step_id not in blocked)

    if blocked:
        return SafetyDecision(
            decision="blocked",
            rationale=(
                "High-risk actions are blocked by the safety boundary; they cannot become "
                "executable merely because a recovery step requests approval."
            ),
            risk_level="high",
            approval_required=False,
            blocked_steps=blocked,
            reviewed_steps=reviewed,
        )

    approval_required = plan.requires_approval
    risk_level = "medium" if any(
        risk == "medium" for risk in effective_risks.values()
    ) else "low"

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
