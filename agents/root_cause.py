from dataclasses import dataclass

from graph.evidence import EvidenceItem
from graph.state import InvestigationState


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


def _evidence_text(items: list[EvidenceItem]) -> list[str]:
    return [
        f"{item.source}: {item.observation}"
        for item in items
    ]


def generate_hypotheses(state: InvestigationState) -> list[Hypothesis]:
    """Generate competing hypotheses without using ground truth."""
    items = list(state.get("evidence_items", []))
    text = " ".join(_evidence_text(items)).lower()
    hypotheses: list[Hypothesis] = []

    for hypothesis_id, statement, signals in _HYPOTHESES:
        supporting = [
            evidence for evidence in items
            if any(signal in (evidence.source + " " + evidence.observation).lower() for signal in signals)
        ]
        contradictions: list[EvidenceItem] = []

        if hypothesis_id == "H2" and "read_request_latency_ms" in text and "healthy" in text:
            contradictions = [item for item in items if "read_request_latency_ms" in item.observation]
        if hypothesis_id == "H3" and "database" in text and "query" in text:
            contradictions = [item for item in items if "query" in (item.source + item.observation).lower()]

        support_score = min(len(supporting) / 4.0, 1.0)
        contradiction_penalty = min(len(contradictions) / 4.0, 0.6)
        confidence = max(0.0, min(1.0, 0.25 + support_score * 0.75 - contradiction_penalty))

        hypotheses.append(Hypothesis(
            hypothesis_id=hypothesis_id,
            statement=statement,
            supporting_evidence=tuple(item.source for item in supporting),
            contradicting_evidence=tuple(item.source for item in contradictions),
            confidence=round(confidence, 3),
            status="supported" if confidence >= 0.6 else "candidate",
        ))

    return sorted(hypotheses, key=lambda hypothesis: hypothesis.confidence, reverse=True)


def run_root_cause_agent(state: InvestigationState) -> dict:
    """Evaluate multiple root-cause hypotheses from shared evidence."""
    hypotheses = generate_hypotheses(state)
    messages = list(state.get("messages", []))
    messages.append(f"Root Cause Agent evaluated {len(hypotheses)} competing hypotheses.")
    return {
        "hypotheses": hypotheses,
        "messages": messages,
        "investigation_status": "hypothesis_evaluation",
    }
