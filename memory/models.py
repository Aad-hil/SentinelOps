from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IncidentMemory:
    """Durable, agent-facing summary of a completed incident investigation."""

    incident_id: str
    service: str
    severity: str
    title: str
    description: str
    root_cause_hypothesis_id: str | None
    root_cause_statement: str | None
    root_cause_confidence: float | None
    resolution_summary: str | None
    recovery_action: str | None
    investigation_status: str = "unknown"
    approval_status: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None

    def to_search_text(self) -> str:
        """Build deterministic text for semantic incident-memory indexing."""
        parts = [
            self.title,
            self.description,
            f"service: {self.service}",
            f"severity: {self.severity}",
        ]
        if self.root_cause_statement:
            parts.append(f"root cause: {self.root_cause_statement}")
        if self.resolution_summary:
            parts.append(f"resolution: {self.resolution_summary}")
        if self.recovery_action:
            parts.append(f"recovery action: {self.recovery_action}")
        return "\n".join(parts)
