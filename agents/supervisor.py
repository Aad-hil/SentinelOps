from graph.state import InvestigationState


INVESTIGATION_TASKS = [
    "telemetry",
    "knowledge",
    "deployment",
    "root_cause",
    "critic",
    "adjudication",
    "recovery",
    "safety",
]


def run_supervisor(state: InvestigationState) -> dict:
    """Create the plan, dispatch investigation agents, then complete."""

    if not state.get("plan"):
        return {
            "plan": list(INVESTIGATION_TASKS),
            "next_agent": INVESTIGATION_TASKS[0],
            "investigation_status": "evidence_collection",
            "messages": [
                "Supervisor created an evidence-collection, hypothesis-evaluation, critique, and adjudication plan."
            ],
        }

    completed = set(state.get("completed_tasks", []))
    evidence_tasks = [
        task for task in INVESTIGATION_TASKS
        if task not in {"root_cause", "critic", "adjudication", "recovery", "safety"}
    ]
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

    if "adjudication" not in completed:
        return {
            "next_agent": "adjudication",
            "investigation_status": "adjudication",
        }

    if "recovery" not in completed:
        return {
            "next_agent": "recovery",
            "investigation_status": "recovery_planning",
        }

    if "safety" not in completed:
        return {
            "next_agent": "safety",
            "investigation_status": "safety_review",
        }

    if state.get("investigation_status") in {"blocked", "approved_for_execution"}:
        return {
            "next_agent": "complete",
            "investigation_status": state["investigation_status"],
        }

    return {
        "next_agent": "complete",
        "investigation_status": (
            "awaiting_human_approval"
            if state.get("approval_required")
            else "complete"
        ),
    }
