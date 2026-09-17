from graph.state import InvestigationState


INVESTIGATION_TASKS = [
    "telemetry",
    "knowledge",
    "deployment",
    "root_cause",
    "critic",
]


def run_supervisor(state: InvestigationState) -> dict:
    """Create the plan, dispatch investigation agents, then complete."""

    if not state.get("plan"):
        return {
            "plan": list(INVESTIGATION_TASKS),
            "next_agent": INVESTIGATION_TASKS[0],
            "investigation_status": "evidence_collection",
            "messages": [
                "Supervisor created an evidence-collection, hypothesis-evaluation, and critique plan."
            ],
        }

    completed = set(state.get("completed_tasks", []))
    evidence_tasks = [task for task in INVESTIGATION_TASKS if task not in {"root_cause", "critic"}]
    remaining = [task for task in evidence_tasks if task not in completed]

    if remaining:
        return {
            "next_agent": remaining[0],
            "investigation_status": "evidence_collection",
        }

    if "root_cause" not in completed:
        return {
            "next_agent": "root_cause",
            "investigation_status": "hypothesis_evaluation",
        }

    if "critic" not in completed:
        return {
            "next_agent": "critic",
            "investigation_status": "critique",
        }

    return {
        "next_agent": "complete",
        "investigation_status": "complete",
    }
