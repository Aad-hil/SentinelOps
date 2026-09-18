from graph.state import InvestigationState


def record_human_approval(
    state: InvestigationState,
    *,
    approved: bool,
    reviewer: str,
) -> dict:
    """Record an operator decision without executing any recovery action."""
    if not reviewer.strip():
        raise ValueError("reviewer is required")

    decision = state.get("safety_decision")
    if decision is None:
        raise ValueError("a safety decision is required before approval")

    if state.get("investigation_status") != "awaiting_human_approval":
        raise ValueError(
            "human approval is only valid while the investigation is awaiting approval"
        )

    if not getattr(decision, "human_approval_required", False):
        raise ValueError("the safety decision does not require human approval")

    if not state.get("approval_required"):
        raise ValueError("human approval is no longer pending")

    status = "approved" if approved else "rejected"
    return {
        "approval_status": status,
        "approval_required": False,
        "investigation_status": "approved_for_execution" if approved else "blocked",
        "messages": list(state.get("messages", []))
        + [f"Human reviewer {reviewer} marked recovery as {status}."],
    }
