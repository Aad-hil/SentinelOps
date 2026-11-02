from __future__ import annotations

from datetime import datetime, timezone

from graph.state import InvestigationState
from memory.models import IncidentMemory


def build_incident_memory(state: InvestigationState) -> IncidentMemory:
    """Build durable memory without claiming a proposed recovery was executed."""
    evidence = state["evidence"]
    incident = evidence.incident
    hypotheses = list(state.get("hypotheses", []))
    adjudication = state.get("adjudication")

    leading = None
    if adjudication is not None:
        leading = next(
            (h for h in hypotheses if h.hypothesis_id == adjudication.hypothesis_id),
            None,
        )
    if leading is None and hypotheses:
        leading = hypotheses[0]

    recovery_plan = state.get("recovery_plan")
    proposed_actions = (
        [step.action.strip() for step in recovery_plan.steps if step.action.strip()]
        if recovery_plan is not None
        else []
    )
    recovery_action = "; ".join(proposed_actions) or None

    # SentinelOps only proposes recovery steps. Human approval does not prove
    # that an operator executed them or that the incident was resolved.
    resolution_summary = None

    completed_at = datetime.now(timezone.utc)
    return IncidentMemory(
        incident_id=incident.incident_id,
        service=incident.service,
        severity=incident.severity,
        title=incident.title,
        description=incident.description,
        root_cause_hypothesis_id=(leading.hypothesis_id if leading else None),
        root_cause_statement=(leading.statement if leading else None),
        root_cause_confidence=(leading.confidence if leading else None),
        resolution_summary=resolution_summary,
        recovery_action=recovery_action,
        investigation_status=state.get("investigation_status", "unknown"),
        approval_status=state.get("approval_status"),
        created_at=incident.detected_at,
        completed_at=completed_at,
    )
