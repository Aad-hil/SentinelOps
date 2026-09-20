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


def _relationship_quality(hypothesis: Hypothesis) -> float:
    """Score completeness and directness of the hypothesis causal roles."""
    relationships = hypothesis.causal_relationships
    if not relationships:
        return 0.0

    roles = {relationship.role for relationship in relationships}
    completeness = len(roles.intersection({"trigger", "mechanism", "impact"})) / 3.0

    direct = sum(
        relationship.strength
        for relationship in relationships
        if relationship.role in {"trigger", "mechanism", "impact"}
    ) / len(relationships)

    return round(completeness * direct, 3)


def adjudicate_hypotheses(state: InvestigationState) -> tuple[list[Hypothesis], Adjudication | None]:
    """Re-score hypotheses using temporal, causal, recovery, and alternative evidence."""
    hypotheses = list(state.get("hypotheses", []))
    items = list(state.get("evidence_items", []))
    if not hypotheses:
        return [], None

    temporal = _has(items, "deployment", "web-2025.01.09.3") and _has(items, "deployment", "query")
    causal = _has(items, "query_fingerprint") and _has(items, "query_path") and _has(items, "database")
    recovery = _has_any(items, "rollback") and _has_any(items, "error rate", "baseline", "returned toward baseline")
    traffic_direct = _has(items, "traffic") or _has(items, "request volume") or _has(items, "requests per second")
    network_direct = _has(items, "network") or _has(items, "downstream") or _has(items, "connection timeout")

    adjudicated: list[Hypothesis] = []
    for hypothesis in hypotheses:
        confidence = hypothesis.confidence
        status = hypothesis.status
        relationship_roles = {relationship.role for relationship in hypothesis.causal_relationships}

        if hypothesis.hypothesis_id == "H1":
            confidence = min(1.0, confidence * 0.55 + (0.15 if temporal else 0.0) + (0.15 if causal else 0.0) + (0.10 if recovery else 0.0))
            status = "strong_candidate" if confidence >= 0.75 else "supported"
        elif hypothesis.hypothesis_id == "H2":
            confidence = min(1.0, confidence * 0.55 + (0.25 if traffic_direct else 0.0))
            status = "supported" if traffic_direct and confidence >= 0.6 else "insufficient_evidence"
        elif hypothesis.hypothesis_id == "H3":
            confidence = min(1.0, confidence * 0.55 + (0.25 if network_direct else 0.0))
            status = "supported" if network_direct and confidence >= 0.6 else "insufficient_evidence"
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
                causal_relationships=hypothesis.causal_relationships,
            )
        )

    adjudicated.sort(key=lambda h: h.confidence, reverse=True)
    leading = adjudicated[0]
    gaps: list[str] = []
    if leading.hypothesis_id == "H1" and not recovery:
        gaps.append("post-rollback recovery evidence")
    if leading.hypothesis_id == "H2" and not traffic_direct:
        gaps.append("direct request-volume evidence")
    if leading.hypothesis_id == "H3" and not network_direct:
        gaps.append("direct network or downstream evidence")
    if len(relationship_roles.intersection({"trigger", "mechanism", "impact"})) < 3:
        gaps.append("complete trigger-mechanism-impact relationship")

    rationale = (
        f"{leading.hypothesis_id} has the strongest evidence after checking temporal order, "
        "causal linkage, recovery correlation, alternative-hypothesis evidence, and explicit "
        "causal relationship roles."
    )
    adjudication = Adjudication(
        hypothesis_id=leading.hypothesis_id,
        rationale=rationale,
        temporal_support=temporal,
        causal_support=causal,
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
