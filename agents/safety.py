from graph.state import AgentFinding, InvestigationState, append_finding
from safety.policy import evaluate_recovery_safety


def run_safety_agent(state: InvestigationState) -> dict:
    """Review a recovery plan against deterministic safety guardrails."""
    decision = evaluate_recovery_safety(state.get("recovery_plan"))
    finding = AgentFinding(
        agent="safety",
        category="safety_review",
        summary=f"Safety review is {decision.decision} at {decision.risk_level} risk.",
        evidence=decision.evidence_gaps,
        confidence=1.0,
    )
    result = append_finding(state, finding)
    approval_status = "pending" if decision.human_approval_required else "not_required"
    result.update(
        {
            "safety_decision": decision,
            "approval_required": decision.human_approval_required,
            "approval_status": approval_status,
            "messages": list(state.get("messages", []))
            + [f"Safety Agent marked recovery as {decision.decision}."],
            "investigation_status": (
                "awaiting_human_approval"
                if decision.human_approval_required
                else "complete"
            ),
        }
    )
    return result
