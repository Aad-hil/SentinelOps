from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceItem:
    """A normalized piece of evidence that agents can exchange."""

    source: str
    evidence_type: str
    observation: str
    timestamp: datetime | None = None
    relevance: float = 0.0
    agent: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must be non-empty")
        if not self.evidence_type.strip():
            raise ValueError("evidence_type must be non-empty")
        if not self.observation.strip():
            raise ValueError("observation must be non-empty")
        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError("relevance must be between 0 and 1")


def append_evidence(
    existing: list[EvidenceItem] | tuple[EvidenceItem, ...],
    new_items: list[EvidenceItem] | tuple[EvidenceItem, ...],
) -> list[EvidenceItem]:
    """Append evidence while avoiding exact duplicate items."""
    result = list(existing)
    for item in new_items:
        if item not in result:
            result.append(item)
    return result
