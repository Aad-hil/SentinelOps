from recovery.models import RecoveryPlan
from recovery.planner import build_recovery_plan
from graph.state import AgentFinding, InvestigationState, append_finding


def run_recovery_agent(state: InvestigationState) -> dict:
    """Turn adjudication output into a conservative recovery recommendation."""
    plan = build_recovery_plan(state)
    finding = AgentFinding(
        agent="recovery",
        category="recovery_planning",
        summary=(
            f"Recovery plan is {plan.readiness} for {plan.incident_id}; "
            f"{len(plan.steps)} step(s) proposed."
        ),
        evidence=tuple(
            evidence
            for step in plan.steps
            for evidence in step.evidence
        ),
        confidence=plan.confidence,
    )
    result = append_finding(state, finding)
    result.update({
        "recovery_plan": plan,
        "messages": list(state.get("messages", [])) + [
            f"Recovery Agent created a {plan.readiness} recovery plan."
        ],
        "investigation_status": "recovery_planning",
    })
    return result
