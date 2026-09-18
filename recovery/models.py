from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryStep:
    """A proposed recovery action that SentinelOps does not execute automatically."""

    step_id: str
    action: str
    purpose: str
    risk: str
    requires_approval: bool
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryPlan:
    """Structured, evidence-aware recovery recommendation for an incident."""

    incident_id: str
    hypothesis_id: str | None
    confidence: float
    readiness: str
    rationale: str
    steps: tuple[RecoveryStep, ...]

    @property
    def requires_approval(self) -> bool:
        return any(step.requires_approval for step in self.steps)
