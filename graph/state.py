from dataclasses import dataclass
from typing import Any, TypedDict

from simulator.evidence import EvidenceBundle

from graph.evidence import EvidenceItem


@dataclass(frozen=True)
class AgentFinding:
    """A structured observation produced by one investigation agent."""

    agent: str
    category: str
    summary: str
    evidence: tuple[str, ...]
    confidence: float


class InvestigationState(TypedDict, total=False):
    """Shared state passed between SentinelOps agents."""

    incident_id: str
    incident_summary: str
    evidence: EvidenceBundle
    knowledge_retriever: Any
    plan: list[str]
    completed_tasks: list[str]
    findings: list[AgentFinding]
    evidence_items: list[EvidenceItem]
    hypotheses: list[Any]
    critique: Any
    messages: list[str]
    next_agent: str
    investigation_status: str


def append_finding(state: InvestigationState, finding: AgentFinding) -> dict[str, Any]:
    """Return a state update containing one additional finding."""
    findings = list(state.get("findings", []))
    findings.append(finding)
    completed = list(state.get("completed_tasks", []))
    completed.append(finding.agent)
    return {"findings": findings, "completed_tasks": completed}


def append_agent_evidence(
    state: InvestigationState,
    items: list[EvidenceItem] | tuple[EvidenceItem, ...],
) -> dict[str, Any]:
    """Return a state update containing new normalized evidence."""
    existing = list(state.get("evidence_items", []))
    for item in items:
        if item not in existing:
            existing.append(item)
    return {"evidence_items": existing}
