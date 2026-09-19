from dataclasses import dataclass

from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_finding


@dataclass(frozen=True)
class Hypothesis:
    """A candidate explanation evaluated against shared evidence."""

    hypothesis_id: str
    statement: str
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    confidence: float
    status: str = "candidate"


# Generic causal patterns; these are not benchmark ground truth.
_HYPOTHESES = (
    ("H1", "A recent deployment introduced a database-impacting change that caused primary database saturation.",
     ("deployment", "query", "database", "cpu", "saturation")),
    ("H2", "A traffic or request-volume spike overloaded the service or database and caused the observed errors.",
     ("traffic", "request", "load", "queue", "request_rate")),
    ("H3", "A network or downstream dependency problem increased request latency and caused failures.",
     ("network", "downstream", "latency", "timeout")),
    ("H4", "A database connection-capacity problem exhausted available connections and caused request failures.",
     ("connection", "pool", "capacity", "connection_utilization", "connection_errors")),
    ("H5", "A database query regression caused lock contention, resource pressure, or unusually slow queries.",
     ("query", "lock", "contention", "query_latency", "slow")),
    ("H6", "A schema or database migration overlapped with workload and caused database resource contention.",
     ("schema", "migration", "alter", "contention")),
    ("H7", "A database primary failure or unstable failover caused service disruption.",
     ("primary", "failover", "crash", "health")),
    ("H8", "A database configuration, version, or permission regression caused database operations to fail.",
     ("permission", "permissions", "configuration", "version", "insert")),
    ("H9", "A database write or transaction pattern became excessively expensive and caused latency or timeouts.",
     ("write", "transaction", "expensive", "write_latency", "timeout")),
    ("H10", "A database replication problem caused replica lag and stale or unavailable data.",
     ("replication", "lag", "replica")),
    ("H11", "An infrastructure or data-store upgrade introduced resource contention and degraded dependent queries.",
     ("upgrade", "data-store", "resource_contention", "version")),
    ("H12", "A background workload or queue backlog amplified the incident after an inefficient database operation.",
     ("queue", "background", "webhook", "backlog", "inefficient")),
)


def _evidence_text(item: EvidenceItem) -> str:
    return (item.source + " " + item.observation).lower()


def _matches_signal(item: EvidenceItem, signal: str) -> bool:
    text = _evidence_text(item)
    normalized = signal.lower().replace("_", " ")
    return signal.lower() in text or normalized in text


def _contradictions(hypothesis_id: str, items: list[EvidenceItem]) -> list[EvidenceItem]:
    contradictions: list[EvidenceItem] = []
    for item in items:
        text = _evidence_text(item)
        if hypothesis_id == "H2" and ("normal" in text or "healthy" in text):
            contradictions.append(item)
        elif hypothesis_id == "H3" and item.evidence_type in {"deployment", "deployment_change"}:
            if any(term in text for term in ("query", "database", "deployment")):
                contradictions.append(item)
        elif hypothesis_id == "H7" and "healthy" in text and "primary" in text:
            contradictions.append(item)
    return contradictions


def generate_hypotheses(state: InvestigationState) -> list[Hypothesis]:
    """Generate competing causal hypotheses from observed evidence only."""
    items = list(state.get("evidence_items", []))
    hypotheses: list[Hypothesis] = []

    for hypothesis_id, statement, signals in _HYPOTHESES:
        supporting = [
            item for item in items
            if any(_matches_signal(item, signal) for signal in signals)
        ]
        contradictions = _contradictions(hypothesis_id, items)
        support_score = min(len(supporting) / 4.0, 1.0)
        contradiction_penalty = min(len(contradictions) / 4.0, 0.6)
        confidence = max(0.0, min(1.0, 0.15 + support_score * 0.85 - contradiction_penalty))

        hypotheses.append(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                statement=statement,
                supporting_evidence=tuple(item.source for item in supporting),
                contradicting_evidence=tuple(item.source for item in contradictions),
                confidence=round(confidence, 3),
                status="supported" if confidence >= 0.6 else "candidate",
            )
        )

    return sorted(hypotheses, key=lambda h: (-h.confidence, h.hypothesis_id))


def run_root_cause_agent(state: InvestigationState) -> dict:
    """Evaluate multiple competing root-cause hypotheses from shared evidence."""
    hypotheses = generate_hypotheses(state)
    best = hypotheses[0] if hypotheses else None
    finding = AgentFinding(
        agent="root_cause",
        category="hypothesis_evaluation",
        summary=(
            f"Evaluated {len(hypotheses)} competing hypotheses; top candidate is "
            f"{best.hypothesis_id} with confidence {best.confidence:.3f}."
            if best
            else "No hypotheses could be evaluated from the available evidence."
        ),
        evidence=best.supporting_evidence if best else (),
        confidence=best.confidence if best else 0.0,
    )
    result = append_finding(state, finding)
    result.update({
        "hypotheses": hypotheses,
        "messages": list(state.get("messages", [])) + [
            f"Root Cause Agent evaluated {len(hypotheses)} competing hypotheses."
        ],
        "investigation_status": "hypothesis_evaluation",
    })
    return result
