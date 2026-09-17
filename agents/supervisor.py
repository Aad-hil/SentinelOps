from graph.state import InvestigationState


INVESTIGATION_TASKS = ["telemetry", "knowledge", "deployment"]


def run_supervisor(state: InvestigationState) -> dict:
    """Create the first investigation plan and dispatch the evidence agents."""

    if not state.get("plan"):
        return {
            "plan": list(INVESTIGATION_TASKS),
            "next_agent": INVESTIGATION_TASKS[0],
            "investigation_status": "evidence_collection",
            "messages": [
                "Supervisor created an independent evidence-collection plan."
            ],
        }

    completed = set(state.get("completed_tasks", []))
    remaining = [task for task in INVESTIGATION_TASKS if task not in completed]
    return {
        "next_agent": remaining[0] if remaining else "complete",
        "investigation_status": "evidence_collection" if remaining else "complete",
    }
