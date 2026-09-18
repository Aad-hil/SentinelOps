from recovery.models import RecoveryPlan, RecoveryStep
from graph.state import InvestigationState


def build_recovery_plan(state: InvestigationState) -> RecoveryPlan:
    """Build a conservative recovery recommendation from adjudication and critique."""
    adjudication = state.get("adjudication")
    critique = state.get("critique")
    incident_id = state.get("incident_id") or state["evidence"].incident.incident_id

    if adjudication is None:
        return RecoveryPlan(
            incident_id=incident_id,
            hypothesis_id=None,
            confidence=0.0,
            readiness="blocked",
            rationale="No adjudicated root-cause hypothesis is available for recovery planning.",
            steps=(
                RecoveryStep(
                    step_id="verify-root-cause",
                    action="Collect additional evidence before changing production state.",
                    purpose="Avoid remediation based on an unvalidated hypothesis.",
                    risk="low",
                    requires_approval=False,
                ),
            ),
        )

    confidence = float(adjudication.confidence)
    hypothesis_id = adjudication.hypothesis_id
    gaps = tuple(adjudication.alternative_gaps)
    missing = tuple(getattr(critique, "missing_evidence", ())) if critique else ()
    unresolved = tuple(dict.fromkeys((*gaps, *missing)))

    if not (
        adjudication.temporal_support
        and adjudication.causal_support
        and adjudication.recovery_support
    ):
        gap_text = "; ".join(unresolved) or "causal and recovery evidence"
        return RecoveryPlan(
            incident_id=incident_id,
            hypothesis_id=hypothesis_id,
            confidence=confidence,
            readiness="verification_required",
            rationale=(
                f"Recovery action is not ready for production execution because the investigation "
                f"has unresolved evidence gaps: {gap_text}."
            ),
            steps=(
                RecoveryStep(
                    step_id="collect-missing-evidence",
                    action="Collect the missing causal, temporal, and recovery evidence.",
                    purpose="Validate the leading hypothesis before remediation.",
                    risk="low",
                    requires_approval=False,
                    evidence=unresolved,
                ),
                RecoveryStep(
                    step_id="prepare-mitigation",
                    action="Prepare a reversible mitigation for human review; do not execute it automatically.",
                    purpose="Reduce incident impact while preserving operator control.",
                    risk="medium",
                    requires_approval=True,
                ),
            ),
        )

    steps = (
        RecoveryStep(
            step_id="mitigate",
            action="Apply the documented mitigation associated with the validated root cause.",
            purpose="Reduce ongoing customer impact.",
            risk="medium",
            requires_approval=True,
        ),
        RecoveryStep(
            step_id="verify-recovery",
            action="Verify error rate, latency, and service health return toward baseline.",
            purpose="Confirm that mitigation restored service health.",
            risk="low",
            requires_approval=False,
        ),
        RecoveryStep(
            step_id="permanent-fix",
            action="Document and validate the permanent fix before production rollout.",
            purpose="Prevent recurrence after immediate recovery.",
            risk="medium",
            requires_approval=True,
        ),
    )
    return RecoveryPlan(
        incident_id=incident_id,
        hypothesis_id=hypothesis_id,
        confidence=confidence,
        readiness="ready_for_review",
        rationale="The leading hypothesis has temporal, causal, and recovery support; proposed actions still require human review where production state may change.",
        steps=steps,
    )
