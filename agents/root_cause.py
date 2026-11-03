from dataclasses import dataclass
from datetime import datetime, timezone

from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_finding


@dataclass(frozen=True)
class CausalEvidenceRelationship:
    """An explicit relationship between evidence and a causal role."""

    source: str
    role: str
    hypothesis_id: str
    strength: float
    rationale: str


@dataclass(frozen=True)
class Hypothesis:
    """A candidate explanation evaluated against shared evidence."""

    hypothesis_id: str
    display_name: str
    statement: str
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    confidence: float
    status: str = "candidate"
    causal_score: float = 0.0
    causal_evidence: tuple[str, ...] = ()
    causal_relationships: tuple[CausalEvidenceRelationship, ...] = ()


def _evidence_text(item: EvidenceItem) -> str:
    return (item.source + " " + item.observation).lower()


def _matches_signal(item: EvidenceItem, signal: str) -> bool:
    """Match signal phrases across common telemetry/key naming conventions."""
    text = _evidence_text(item)
    normalized_text = text.replace("_", " ").replace("-", " ")
    normalized_signal = signal.lower().replace("_", " ").replace("-", " ")
    return signal.lower() in text or normalized_signal in normalized_text


def _timestamp_key(item: EvidenceItem) -> datetime:
    """Return a comparable UTC timestamp for aware or naive evidence times."""
    timestamp = item.timestamp
    if timestamp is None:
        return datetime.max.replace(tzinfo=timezone.utc)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _generate_redshift_hypotheses(state: InvestigationState) -> list[Hypothesis]:
    """Rank Redshift candidates from trigger, mechanism, and impact evidence."""
    from agents.redshift_hypotheses import REDSHIFT_HYPOTHESES

    items = list(state.get("evidence_items", []))
    results: list[Hypothesis] = []
    for definition in REDSHIFT_HYPOTHESES:
        stages = (
            definition.trigger_signals,
            definition.mechanism_signals,
            definition.impact_signals,
        )
        matches = [
            [item for item in items if any(_matches_signal(item, signal) for signal in signals)]
            for signals in stages
        ]
        # RSH12 is a fallback classification, never a keyword competitor.
        if definition.hypothesis_id == "RSH12":
            covered = sum(bool(stage) for stage in matches[:3])
            score = 0.12 if covered < 2 else 0.08
            relationships = ()
        else:
            covered = sum(bool(stage) for stage in matches)
            score = covered / 3.0
            relationships = tuple(
                CausalEvidenceRelationship(
                    source=item.source,
                    role=role,
                    hypothesis_id=definition.hypothesis_id,
                    strength=0.75 if item.evidence_type in {"deployment", "deployment_change"} and role == "trigger" else 0.6,
                    rationale=f"Evidence matches Redshift {role} signals for {definition.hypothesis_id}.",
                )
                for role, stage in zip(("trigger", "mechanism", "impact"), matches)
                for item in stage
            )
        supporting = tuple(dict.fromkeys(item.source for stage in matches for item in stage))
        causal_sources = tuple(dict.fromkeys(
            relationship.source for relationship in relationships
        ))
        # Separate initiating evidence from downstream symptoms. In particular,
        # COPY errors are an impact for authorization failures too; they must not
        # outweigh an explicit IAM/KMS policy change.
        direct_trigger = any(
            item.evidence_type in {"deployment", "deployment_change"}
            and any(_matches_signal(item, signal) for signal in definition.trigger_signals)
            for item in items
        )
        mechanism_evidence = [
            item for item in matches[1]
            if item.evidence_type not in {"metric", "trace"}
        ]
        trigger_evidence = [
            item for item in matches[0]
            if item.evidence_type in {"deployment", "deployment_change"}
        ]
        impact_evidence = matches[2]
        score = (
            (0.45 if trigger_evidence else 0.0)
            + (0.35 if mechanism_evidence else 0.0)
            + (0.20 if impact_evidence else 0.0)
        )
        relationships = tuple(
            CausalEvidenceRelationship(
                source=item.source,
                role=role,
                hypothesis_id=definition.hypothesis_id,
                strength=0.85 if role == "trigger" else 0.6,
                rationale=f"Evidence matches Redshift {role} signals for {definition.hypothesis_id}.",
            )
            for role, stage in (
                ("trigger", trigger_evidence),
                ("mechanism", mechanism_evidence),
                ("impact", impact_evidence),
            )
            for item in stage
        )
        supporting = tuple(dict.fromkeys(
            item.source for stage in matches for item in stage
        ))
        causal_sources = tuple(dict.fromkeys(
            relationship.source for relationship in relationships
        ))
        confidence = min(
            0.99,
            0.10 + score * 0.68
            + min(len(supporting), 5) * 0.012
            + (0.16 if direct_trigger else 0.0),
        )
        results.append(Hypothesis(
            hypothesis_id=definition.hypothesis_id,
            display_name=definition.name,
            statement=definition.statement,
            supporting_evidence=supporting,
            contradicting_evidence=(),
            confidence=round(confidence, 3),
            status="supported" if covered == 3 and confidence >= 0.6 else "candidate",
            causal_score=round(score, 3),
            causal_evidence=causal_sources,
            causal_relationships=relationships,
        ))
    # Require a genuinely discriminating event or mechanism before naming a
    # specific cause. Generic query/runtime/error wording is impact evidence only.
    generic_only = {
        "query", "runtime", "error", "latency", "duration",
        "workload", "load", "failure", "redshift",
    }
    has_specific_change = any(
        item.evidence_type in {"deployment", "deployment_change"}
        and any(
            _matches_signal(item, signal)
            for definition in REDSHIFT_HYPOTHESES
            if definition.hypothesis_id != "RSH12"
            for signal in definition.trigger_signals
            if signal not in generic_only
        )
        for item in items
    )
    has_specific_mechanism = any(
        item.evidence_type in {"log", "deployment", "deployment_change"}
        and any(
            _matches_signal(item, signal)
            for definition in REDSHIFT_HYPOTHESES
            if definition.hypothesis_id != "RSH12"
            for signal in definition.mechanism_signals
            if signal not in generic_only
        )
        for item in items
    )
    if not has_specific_change and not has_specific_mechanism:
        results = [
            Hypothesis(
                hypothesis_id=item.hypothesis_id,
                display_name=item.display_name,
                statement=item.statement,
                supporting_evidence=item.supporting_evidence,
                contradicting_evidence=item.contradicting_evidence,
                confidence=0.68 if item.hypothesis_id == "RSH12" else min(item.confidence, 0.35),
                status="candidate",
                causal_score=item.causal_score,
                causal_evidence=item.causal_evidence,
                causal_relationships=item.causal_relationships,
            )
            for item in results
        ]

    best_known_coverage = max(
        (
            sum(
                any(any(_matches_signal(item, signal) for signal in stage) for item in items)
                for stage in (
                    definition.trigger_signals,
                    definition.mechanism_signals,
                    definition.impact_signals,
                )
            )
            for definition in REDSHIFT_HYPOTHESES
            if definition.hypothesis_id != "RSH12"
        ),
        default=0,
    )
    if best_known_coverage < 2:
        results = [
            Hypothesis(
                hypothesis_id=item.hypothesis_id,
                display_name=item.display_name,
                statement=item.statement,
                supporting_evidence=item.supporting_evidence,
                contradicting_evidence=item.contradicting_evidence,
                confidence=0.68 if item.hypothesis_id == "RSH12" else min(item.confidence, 0.35),
                status="candidate",
                causal_score=item.causal_score,
                causal_evidence=item.causal_evidence,
                causal_relationships=item.causal_relationships,
            )
            for item in results
        ]
    return sorted(results, key=lambda h: (-h.confidence, h.hypothesis_id))


def generate_hypotheses(state: InvestigationState) -> list[Hypothesis]:
    """Generate domain-specific candidates from observed evidence only."""
    evidence = state.get("evidence")
    incident = getattr(evidence, "incident", None)
    if incident is None or incident.service != "amazon-redshift":
        raise ValueError(
            "SentinelOps currently supports Amazon Redshift incidents only."
        )
    return _generate_redshift_hypotheses(state)



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
    from agents.llm import ask, evidence_context
    explanation = ask(
        "You are a Redshift RCA analyst. Explain only the supplied observed evidence. "
        "The deterministic hypothesis ranking is authoritative. Never claim recovery is authorized. "
        "Cite evidence sources exactly; distinguish inference from observation. Reply in under 120 words.",
        f"Leading hypothesis: {best.hypothesis_id if best else 'none'}; "
        f"statement: {best.statement if best else 'none'}; "
        f"score: {best.confidence if best else 0}.\nEvidence:\n{evidence_context(state)}",
    ) if best else None
    if explanation:
        finding = AgentFinding(agent="root_cause_llm", category="llm_explanation",
            summary=explanation, evidence=best.supporting_evidence, confidence=best.confidence)
    result = append_finding(state, finding)
    result.update({
        "hypotheses": hypotheses,
        "messages": list(state.get("messages", [])) + [
            f"Root Cause Agent evaluated {len(hypotheses)} competing hypotheses with causal-chain scoring."
            + (" Ollama provided an evidence explanation." if explanation else " Deterministic mode; no LLM explanation.")
        ],
        "investigation_status": "hypothesis_evaluation",
    })
    return result
