from __future__ import annotations

from datetime import datetime, timezone

from graph.state import InvestigationState
from memory.models import IncidentMemory


def build_incident_memory(state: InvestigationState) -> IncidentMemory:
    """Build durable incident memory from a completed agent-facing state."""
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

    recovery_action = None
    resolution_summary = None
    if adjudication is not None:
        recovery_action = (
            "Rollback the problematic deployment and verify service recovery."
            if adjudication.recovery_support
            else None
        )
        resolution_summary = adjudication.rationale

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
