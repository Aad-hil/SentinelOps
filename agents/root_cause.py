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


_HYPOTHESES = (
    (
        "H1",
        "A recent deployment introduced a database-impacting change that caused primary database saturation.",
        ("deployment", "query", "database", "cpu", "saturation"),
    ),
    (
        "H2",
        "A traffic spike overloaded the service or database and caused the observed errors.",
        ("traffic", "request", "load", "queue"),
    ),
    (
        "H3",
        "A network or downstream dependency problem increased request latency and caused failures.",
        ("network", "latency", "timeout", "connection"),
    ),
)


def generate_hypotheses(state: InvestigationState) -> list[Hypothesis]:
    """Generate competing hypotheses without using ground truth."""
    items = list(state.get("evidence_items", []))
    hypotheses: list[Hypothesis] = []

    for hypothesis_id, statement, signals in _HYPOTHESES:
        supporting = [
            item for item in items
            if any(signal in (item.source + " " + item.observation).lower() for signal in signals)
        ]
        contradictions: list[EvidenceItem] = []

        if hypothesis_id == "H2":
            contradictions = [
                item for item in items
                if "normal" in item.observation.lower() or "healthy" in item.observation.lower()
            ]
        elif hypothesis_id == "H3":
            contradictions = [
                item for item in items
                if "query" in (item.source + " " + item.observation).lower()
                and item.evidence_type in {"deployment", "deployment_change", "knowledge"}
            ]

        support_score = min(len(supporting) / 4.0, 1.0)
        contradiction_penalty = min(len(contradictions) / 4.0, 0.6)
        confidence = max(0.0, min(1.0, 0.25 + support_score * 0.75 - contradiction_penalty))

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

    return sorted(hypotheses, key=lambda hypothesis: hypothesis.confidence, reverse=True)


def run_root_cause_agent(state: InvestigationState) -> dict:
    """Evaluate multiple root-cause hypotheses from shared evidence."""
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
