from dataclasses import dataclass

from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_finding
from agents.root_cause import Hypothesis


@dataclass(frozen=True)
class Adjudication:
    """Final evidence-quality assessment of competing root-cause hypotheses."""

    hypothesis_id: str
    rationale: str
    temporal_support: bool
    causal_support: bool
    recovery_support: bool
    alternative_gaps: tuple[str, ...]
    confidence: float


def _text(item: EvidenceItem) -> str:
    return f"{item.source} {item.observation}".lower()


def _has(items: list[EvidenceItem], *terms: str) -> bool:
    return any(all(term.lower() in _text(item) for term in terms) for item in items)


def _has_any(items: list[EvidenceItem], *terms: str) -> bool:
    return any(term.lower() in _text(item) for item in items for term in terms)


def _recovery_signal_support(items: list[EvidenceItem]) -> bool:
    """Return whether evidence contains a concrete mitigation/recovery signal."""
    signals = (
        "mitigation",
        "rollback",
        "restart",
        "revert",
        "throttle",
        "terminate",
        "kill",
        "recover",
    )
    return _has_any(items, *signals)


def adjudicate_hypotheses(state: InvestigationState) -> tuple[list[Hypothesis], Adjudication | None]:
    """Adjudicate hypotheses using causal-chain quality instead of benchmark-specific IDs."""
    hypotheses = list(state.get("hypotheses", []))
    items = list(state.get("evidence_items", []))
    if not hypotheses:
        return [], None

    recovery = _recovery_signal_support(items)
    incident_started = state.get("evidence").incident.started_at if state.get("evidence") else None

    adjudicated: list[Hypothesis] = []
    for hypothesis in hypotheses:
        confidence = hypothesis.confidence

        # Causal-chain quality is the strongest discriminator. Evidence quantity
        # remains represented by the hypothesis confidence, while recovery
        # signals provide a small bonus when a concrete mitigation signal exists.
        confidence = min(
            1.0,
            confidence * 0.55
            + hypothesis.causal_score * 0.35
            + (0.10 if recovery and hypothesis.causal_score >= 0.667 else 0.0),
        )

        # A causal chain that ends before the incident is not sufficient for
        # production recovery, even when the lexical evidence is strong.
        if incident_started is not None and hypothesis.causal_evidence:
            supporting_times = [
                item.timestamp
                for item in items
                if item.source in hypothesis.causal_evidence and item.timestamp is not None
            ]
            if supporting_times and max(supporting_times) < incident_started:
                confidence *= 0.8

        status = "strong_candidate" if confidence >= 0.75 else (
            "supported" if confidence >= 0.6 else "insufficient_evidence"
        )
        adjudicated.append(
            Hypothesis(
                hypothesis_id=hypothesis.hypothesis_id,
                statement=hypothesis.statement,
                supporting_evidence=hypothesis.supporting_evidence,
                contradicting_evidence=hypothesis.contradicting_evidence,
                confidence=round(confidence, 3),
                status=status,
                causal_score=hypothesis.causal_score,
                causal_evidence=hypothesis.causal_evidence,
            )
        )

    adjudicated.sort(key=lambda h: (-h.confidence, h.hypothesis_id))
    leading = adjudicated[0]

    gaps: list[str] = []
    if leading.causal_score < 1.0:
        gaps.append("complete chronological causal chain")
    if not recovery:
        gaps.append("concrete recovery or mitigation evidence")

    rationale = (
        f"{leading.hypothesis_id} has the strongest evidence after comparing "
        "causal-chain coverage, evidence support, temporal ordering, and recovery signals."
    )
    adjudication = Adjudication(
        hypothesis_id=leading.hypothesis_id,
        rationale=rationale,
        temporal_support=leading.causal_score >= 0.667,
        causal_support=leading.causal_score >= 0.667,
        recovery_support=recovery,
        alternative_gaps=tuple(gaps),
        confidence=round(leading.confidence, 3),
    )
    return adjudicated, adjudication


def run_adjudication_agent(state: InvestigationState) -> dict:
    """Adjudicate competing hypotheses using evidence quality rather than counts alone."""
    hypotheses, adjudication = adjudicate_hypotheses(state)
    if adjudication is None:
        finding = AgentFinding(
            agent="adjudication",
            category="hypothesis_adjudication",
            summary="No hypotheses were available for adjudication.",
            evidence=(),
            confidence=0.0,
        )
    else:
        leading = next(h for h in hypotheses if h.hypothesis_id == adjudication.hypothesis_id)
        finding = AgentFinding(
            agent="adjudication",
            category="hypothesis_adjudication",
            summary=(
                f"Adjudicated {len(hypotheses)} hypotheses; {leading.hypothesis_id} is the leading candidate "
                f"at confidence {leading.confidence:.3f}. "
                f"Temporal={adjudication.temporal_support}, causal={adjudication.causal_support}, "
                f"recovery={adjudication.recovery_support}."
            ),
            evidence=leading.supporting_evidence,
            confidence=adjudication.confidence,
        )

    result = append_finding(state, finding)
    result.update(
        {
            "hypotheses": hypotheses,
            "adjudication": adjudication,
            "messages": list(state.get("messages", []))
            + ["Adjudication Agent re-evaluated competing hypotheses using evidence quality."],
            "investigation_status": "adjudication",
        }
    )
    return result
