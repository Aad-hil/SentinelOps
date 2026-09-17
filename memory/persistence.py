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
    """Persist a completed investigation in structured and semantic memory."""
    if state.get("investigation_status") != "complete":
        return

    memory = build_incident_memory(state)
    repository.initialize()
    repository.save(memory)

    if semantic_repository is not None:
        semantic_repository.index(memory)
