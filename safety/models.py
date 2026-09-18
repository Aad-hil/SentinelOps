from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyDecision:
    """Deterministic safety review of a proposed recovery plan."""

    decision: str
    rationale: str
    risk_level: str
    approval_required: bool
    blocked_steps: tuple[str, ...] = ()
    reviewed_steps: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()

    @property
    def human_approval_required(self) -> bool:
        return self.approval_required and self.decision == "review_required"
