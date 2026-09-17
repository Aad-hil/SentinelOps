from __future__ import annotations

from graph.state import InvestigationState
from memory.builders import build_incident_memory
from memory.postgres import PostgresIncidentMemoryRepository


def persist_completed_investigation(
    state: InvestigationState,
    repository: PostgresIncidentMemoryRepository,
) -> None:
    """Persist an investigation only after it reaches the completed state."""
    if state.get("investigation_status") != "complete":
        return

    memory = build_incident_memory(state)
    repository.initialize()
    repository.save(memory)
