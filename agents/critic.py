from dataclasses import dataclass

from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_finding


@dataclass(frozen=True)
class Critique:
    """Structured challenge to the leading root-cause hypothesis."""

    hypothesis_id: str
    challenge: str
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    confidence: float


def _find_evidence(items: list[EvidenceItem], *terms: str) -> list[EvidenceItem]:
    normalized_terms = tuple(term.lower() for term in terms)
    return [
        item
        for item in items
        if all(term in (item.source + " " + item.observation).lower() for term in normalized_terms)
    ]


def critique_leading_hypothesis(state: InvestigationState) -> Critique | None:
    """Challenge the highest-confidence hypothesis without using ground truth."""
    hypotheses = list(state.get("hypotheses", []))
    if not hypotheses:
        return None

    leading = hypotheses[0]
    items = list(state.get("evidence_items", []))
    supporting = [
        item for item in items
        if item.source in leading.supporting_evidence
    ]

    contradictions = [
        item for item in items
        if item.source in leading.contradicting_evidence
    ]

    missing: list[str] = []
    statement = leading.statement.lower()
    if "deployment" in statement:
        if not _find_evidence(items, "deployment"):
            missing.append("deployment timing or change evidence")
        if not any("query" in (item.source + " " + item.observation).lower() for item in items):
            missing.append("evidence linking the deployment to a specific database query")
    if "traffic" in statement and not _find_evidence(items, "traffic"):
        missing.append("request-volume evidence showing a traffic increase")
    if "network" in statement and not _find_evidence(items, "network"):
        missing.append("network or downstream dependency evidence")

    if not contradictions and not missing:
        challenge = "The leading hypothesis is supported, but the available evidence should still be checked for causal timing and recovery correlation."
        missing.append("causal timing and recovery correlation")
    elif contradictions:
        challenge = "The leading hypothesis has direct contradictions that must be resolved before treating it as established."
    else:
        challenge = "The leading hypothesis has supporting evidence, but key evidence is still missing to establish causality."

    confidence = max(
        0.0,
        min(
            1.0,
            leading.confidence
            - min(len(contradictions) * 0.15, 0.45)
            - min(len(missing) * 0.05, 0.25),
        ),
    )

    return Critique(
        hypothesis_id=leading.hypothesis_id,
        challenge=challenge,
        supporting_evidence=tuple(item.source for item in supporting),
        contradictions=tuple(item.source for item in contradictions),
        missing_evidence=tuple(dict.fromkeys(missing)),
        confidence=round(confidence, 3),
    )


def run_critic_agent(state: InvestigationState) -> dict:
    """Challenge the leading hypothesis and publish the critique as a finding."""
    critique = critique_leading_hypothesis(state)
    if critique is None:
        finding = AgentFinding(
            agent="critic",
            category="critique",
            summary="No root-cause hypothesis was available to challenge.",
            evidence=(),
            confidence=0.0,
        )
    else:
        evidence = critique.supporting_evidence + critique.contradictions
        finding = AgentFinding(
            agent="critic",
            category="critique",
            summary=(
                f"Critic challenged {critique.hypothesis_id}: {critique.challenge} "
                f"Missing evidence: {', '.join(critique.missing_evidence) or 'none identified'}."
            ),
            evidence=evidence,
            confidence=critique.confidence,
        )

    result = append_finding(state, finding)
    result.update({
        "critique": critique,
        "messages": list(state.get("messages", [])) + [
            "Critic Agent challenged the leading root-cause hypothesis."
        ],
        "investigation_status": "critique",
    })
    return result
