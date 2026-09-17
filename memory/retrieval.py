"""Historical incident retrieval helpers for investigation agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from memory.semantic import QdrantIncidentMemoryRepository


@dataclass(frozen=True)
class HistoricalIncidentMatch:
    """A semantically similar completed incident, kept separate from live evidence."""

    incident_id: str
    score: float
    title: str
    service: str
    severity: str
    description: str
    root_cause_statement: str | None
    root_cause_confidence: float | None
    resolution_summary: str | None
    recovery_action: str | None

    @classmethod
    def from_point(cls, point: Any) -> "HistoricalIncidentMatch":
        payload = point.payload or {}
        return cls(
            incident_id=str(payload.get("incident_id", "unknown")),
            score=float(point.score),
            title=str(payload.get("title", "Untitled incident")),
            service=str(payload.get("service", "unknown")),
            severity=str(payload.get("severity", "unknown")),
            description=str(payload.get("description", "")),
            root_cause_statement=payload.get("root_cause_statement"),
            root_cause_confidence=(
                float(payload["root_cause_confidence"])
                if payload.get("root_cause_confidence") is not None
                else None
            ),
            resolution_summary=payload.get("resolution_summary"),
            recovery_action=payload.get("recovery_action"),
        )


def retrieve_historical_incidents(
    repository: QdrantIncidentMemoryRepository,
    query: str,
    *,
    limit: int = 3,
    exclude_incident_id: str | None = None,
) -> list[HistoricalIncidentMatch]:
    """Retrieve relevant historical incidents without treating them as live evidence."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    points = repository.search(query, limit=limit + (1 if exclude_incident_id else 0))
    matches = [HistoricalIncidentMatch.from_point(point) for point in points]
    if exclude_incident_id is not None:
        matches = [
            match for match in matches
            if match.incident_id != exclude_incident_id
        ]
    return matches[:limit]
