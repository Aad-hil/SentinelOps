from langgraph.types import interrupt

from graph.state import InvestigationState
from safety.approval import record_human_approval


def run_human_approval_checkpoint(
    state: InvestigationState,
) -> dict:
    """Pause for operator approval when the graph has a resumable thread."""
    if not state.get("approval_required"):
        return {}

    decision = interrupt(
        {
            "type": "recovery_approval",
            "incident_id": state.get("incident_id"),
            "message": "SentinelOps is requesting human approval for the proposed recovery plan.",
            "decision": (
                state["safety_decision"].decision
                if state.get("safety_decision") is not None
                else None
            ),
            "risk_level": (
                state["safety_decision"].risk_level
                if state.get("safety_decision") is not None
                else None
            ),
            "recovery_plan": state.get("recovery_plan"),
            "instructions": "Resume with {'approved': true|false, 'reviewer': '<name>'}.",
        }
    )

    if not isinstance(decision, dict):
        raise ValueError("human approval response must be a dictionary")

    approved = decision.get("approved")
    reviewer = decision.get("reviewer")
    if not isinstance(approved, bool):
        raise ValueError("human approval response must include boolean 'approved'")
    if not isinstance(reviewer, str):
        raise ValueError("human approval response must include string 'reviewer'")

    return record_human_approval(
        state,
        approved=approved,
        reviewer=reviewer,
    )
