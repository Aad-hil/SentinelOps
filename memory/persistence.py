from __future__ import annotations

from graph.state import InvestigationState
from memory.builders import build_incident_memory
from memory.postgres import PostgresIncidentMemoryRepository
from memory.semantic import QdrantIncidentMemoryRepository


def persist_completed_investigation(
    state: InvestigationState,
    repository: PostgresIncidentMemoryRepository,
    semantic_repository: QdrantIncidentMemoryRepository | None = None,
) -> None:
    """Persist investigation results once analysis is complete, including approval-pending state."""
    if state.get("investigation_status") not in {\n        "complete",\n        "awaiting_human_approval",\n        "approved_for_execution",\n        "blocked",\n    }:
        return

    memory = build_incident_memory(state)
    repository.initialize()
    repository.save(memory)

    if semantic_repository is not None:
        semantic_repository.index(memory)
