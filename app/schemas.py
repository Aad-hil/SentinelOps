"""Public API schemas for SentinelOps investigation results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CausalRelationshipResponse(BaseModel):
    source: str
    role: str
    hypothesis_id: str
    strength: float
    rationale: str


class EvidenceResponse(BaseModel):
    source: str
    evidence_type: str
    observation: str
    timestamp: datetime | None = None
    relevance: float
    agent: str


class HypothesisResponse(BaseModel):
    hypothesis_id: str
    statement: str
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    confidence: float
    status: str
    causal_score: float
    causal_evidence: list[str] = Field(default_factory=list)
    causal_relationships: list[CausalRelationshipResponse] = Field(default_factory=list)


class AdjudicationResponse(BaseModel):
    hypothesis_id: str
    rationale: str
    temporal_support: bool
    causal_support: bool
    recovery_support: bool
    alternative_gaps: list[str] = Field(default_factory=list)
    confidence: float


class RecoveryStepResponse(BaseModel):
    step_id: str
    action: str
    purpose: str
    risk: str
    requires_approval: bool
    evidence: list[str] = Field(default_factory=list)


class RecoveryPlanResponse(BaseModel):
    incident_id: str
    hypothesis_id: str | None
    confidence: float
    readiness: str
    rationale: str
    steps: list[RecoveryStepResponse] = Field(default_factory=list)


class SafetyDecisionResponse(BaseModel):
    decision: str
    rationale: str
    risk_level: str
    approval_required: bool
    blocked_steps: list[str] = Field(default_factory=list)
    reviewed_steps: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)




class ObservabilityEventResponse(BaseModel):
    """Structured execution event emitted by an investigation graph node."""

    trace_id: str
    incident_id: str | None = None
    node: str
    status: str
    timestamp: datetime
    duration_ms: float
    output_keys: list[str] = Field(default_factory=list)
    error: str | None = None


class InvestigationResponse(BaseModel):
    """Stable public contract for one SentinelOps investigation."""

    incident_id: str
    status: str
    approval_status: str = "not_required"
    approval_required: bool = False
    root_cause: AdjudicationResponse | None = None
    hypotheses: list[HypothesisResponse] = Field(default_factory=list)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    recovery_plan: RecoveryPlanResponse | None = None
    safety_decision: SafetyDecisionResponse | None = None
    messages: list[str] = Field(default_factory=list)
    observability_events: list[ObservabilityEventResponse] = Field(default_factory=list)
    trace_id: str | None = None


class ApprovalRequest(BaseModel):
    """Human decision for a pending recovery approval checkpoint."""

    approved: bool
    reviewer: str = Field(min_length=1)


class ApprovalResponse(BaseModel):
    """Result of resuming an investigation after human review."""

    incident_id: str
    status: str
    approval_status: str
    approval_required: bool
    reviewer: str
    approved: bool
