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
    if state.get("safety_decision") is None:
        raise ValueError("a safety decision is required before approval")
    status = "approved" if approved else "rejected"
    return {
        "approval_status": status,
        "approval_required": False,
        "investigation_status": "approved_for_execution" if approved else "blocked",
        "messages": list(state.get("messages", []))
        + [f"Human reviewer {reviewer} marked recovery as {status}."],
    }
