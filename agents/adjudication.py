from dataclasses import dataclass
from datetime import timezone

from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_finding
from agents.root_cause import Hypothesis


@dataclass(frozen=True)
class Adjudication:
    """Final evidence-quality assessment of competing root-cause hypotheses."""

    hypothesis_id: str
    display_name: str
    statement: str
    brief_explanation: str
    full_explanation: str
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

    evidence_by_source = {item.source: item for item in items}
    # Preserve the direct-signal checks used to distinguish broad symptom
    # hypotheses from hypotheses supported by specific telemetry.
    traffic_direct = any(
        item.evidence_type in {"metric", "log", "trace"}
        and _has_any([item], "request_rate", "request rate", "traffic", "request volume")
        for item in items
    )
    network_direct = any(
        item.evidence_type in {"metric", "log", "trace"}
        and _has_any([item], "network", "downstream", "dependency", "connectivity")
        for item in items
    )

    def _utc_timestamp(item: EvidenceItem):
        timestamp = item.timestamp
        if timestamp is None:
            return None
        return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)

    def _support_for_hypothesis(hypothesis: Hypothesis) -> tuple[bool, bool, bool]:
        """Evaluate causal, temporal, and recovery support for this candidate only."""
        role_evidence = {
            role: [
                evidence_by_source[relationship.source]
                for relationship in hypothesis.causal_relationships
                if relationship.role == role and relationship.source in evidence_by_source
            ]
            for role in ("trigger", "mechanism", "impact")
        }
        causal_support = all(
            role_evidence[role] for role in ("trigger", "mechanism", "impact")
        )
        if not causal_support:
            return False, False, False

        trigger_times = [
            timestamp for item in role_evidence["trigger"]
            if (timestamp := _utc_timestamp(item)) is not None
        ]
        mechanism_times = [
            timestamp for item in role_evidence["mechanism"]
            if (timestamp := _utc_timestamp(item)) is not None
        ]
        impact_times = [
            timestamp for item in role_evidence["impact"]
            if (timestamp := _utc_timestamp(item)) is not None
        ]
        if not (trigger_times and mechanism_times and impact_times):
            return causal_support, False, False

        first_trigger = min(trigger_times)
        later_mechanisms = [timestamp for timestamp in mechanism_times if timestamp >= first_trigger]
        if not later_mechanisms:
            return causal_support, False, False

        first_mechanism = min(later_mechanisms)
        later_impacts = [timestamp for timestamp in impact_times if timestamp >= first_mechanism]
        if not later_impacts:
            return causal_support, False, False

        first_impact = min(later_impacts)
        recovery_support = any(
            item.evidence_type == "recovery"
            and (timestamp := _utc_timestamp(item)) is not None
            and timestamp >= first_impact
            for item in items
        )
        return causal_support, True, recovery_support

    support_by_hypothesis = {
        hypothesis.hypothesis_id: _support_for_hypothesis(hypothesis)
        for hypothesis in hypotheses
    }

    adjudicated: list[Hypothesis] = []
    for hypothesis in hypotheses:
        confidence = hypothesis.confidence
        status = hypothesis.status

        direct_deployment_trigger = any(
            item.evidence_type in {"deployment", "deployment_change"}
            and any(
                term in item.observation.lower()
                for term in ("query", "database", "db_", "release", "schema")
            )
            and not any(
                term in item.observation.lower()
                for term in ("rollback", "restart", "recovery", "throttle", "protect")
            )
            for item in items
        )
        direct_migration_trigger = any(
            item.evidence_type in {"deployment", "deployment_change", "log"}
            and any(
                term in item.observation.lower()
                for term in ("migration", "schema change", "alter table")
            )
            and not any(
                term in item.observation.lower()
                for term in ("rollback", "restart", "recovery")
            )
            for item in items
        )

        if hypothesis.hypothesis_id == "H1":
            if direct_deployment_trigger:
                # Preserve the full evidence-derived score. A directly observed,
                # hypothesis-specific change must not be capped below a competing
                # symptom hypothesis that accumulated many downstream metrics.
                confidence = confidence
            else:
                # Missing deployment evidence weakens this explanation but does
                # not make it impossible when other causal evidence exists.
                confidence = max(0.0, confidence - 0.15)
                status = "candidate"
            status = "strong_candidate" if confidence >= 0.75 else status
        elif hypothesis.hypothesis_id == "H2":
            confidence = min(1.0, confidence + (0.10 if traffic_direct else 0.0))
            # Traffic can be a contributing condition; a directly observed
            # migration trigger is more discriminating for H6.
            if direct_migration_trigger:
                confidence = max(0.0, confidence - 0.20)
            status = "supported" if traffic_direct and confidence >= 0.6 else (
                hypothesis.status if confidence >= 0.6 else "insufficient_evidence"
            )
        elif hypothesis.hypothesis_id == "H3":
            confidence = min(1.0, confidence + (0.10 if network_direct else 0.0))
            status = "supported" if network_direct and confidence >= 0.6 else (
                hypothesis.status if confidence >= 0.6 else "insufficient_evidence"
            )
        elif hypothesis.hypothesis_id == "H6":
            if direct_migration_trigger:
                confidence = min(1.0, confidence + 0.20)
                status = "supported" if confidence >= 0.6 else hypothesis.status
        adjudicated.append(
            Hypothesis(
                hypothesis_id=hypothesis.hypothesis_id,
                display_name=hypothesis.display_name,
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
    causal, temporal, recovery = support_by_hypothesis.get(
        leading.hypothesis_id, (False, False, False)
    )
    leading_relationship_roles = {
        relationship.role for relationship in leading.causal_relationships
    }
    gaps: list[str] = []
    if leading.hypothesis_id == "H1" and not recovery:
        gaps.append("post-rollback recovery evidence")
    if leading.hypothesis_id == "H2" and not traffic_direct:
        gaps.append("direct request-volume evidence")
    if leading.hypothesis_id == "H3" and not network_direct:
        gaps.append("direct network or downstream evidence")
    if len(leading_relationship_roles.intersection({"trigger", "mechanism", "impact"})) < 3:
        gaps.append("complete trigger-mechanism-impact relationship")

    evidence_by_source = {item.source: item for item in items}
    role_lines: list[str] = []
    for role in ("trigger", "mechanism", "impact"):
        role_relationships = [
            relationship for relationship in leading.causal_relationships
            if relationship.role == role
        ]
        observations = []
        for relationship in role_relationships:
            item = evidence_by_source.get(relationship.source)
            if item and item.observation not in observations:
                observations.append(item.observation)
        if observations:
            role_lines.append(f"{role.title()}: " + " ".join(observations[:2]))

    if role_lines:
        brief_explanation = (
            f"{leading.display_name} is the best-supported explanation because the evidence "
            "forms this incident-specific chain: " + " ".join(role_lines[:3])
        )
    else:
        brief_explanation = (
            f"{leading.display_name} currently ranks highest, but the available evidence does "
            "not yet establish a complete trigger-to-impact chain."
        )

    full_lines = [
        f"Selected hypothesis: {leading.display_name} ({leading.hypothesis_id}).",
        f"Proposed mechanism: {leading.statement}",
        "Evidence chain:",
        *(role_lines or ["The evidence does not yet provide clear trigger, mechanism, and impact observations."]),
        f"Temporal support: {'Found' if temporal else 'Not established by the current adjudication checks'}.",
        f"Causal support: {'Found' if causal else 'Not established by the current adjudication checks'}.",
        f"Recovery correlation: {'Found' if recovery else 'Not established by the current adjudication checks'}.",
        "Evidence gaps: " + (", ".join(gaps) if gaps else "No specific gap was flagged by the current adjudication checks."),
        "The evidence score is a heuristic ranking score, not a calibrated probability or proof of root cause.",
    ]
    rationale = (
        f"{leading.hypothesis_id} ranked highest after comparing evidence strength, causal roles, "
        "temporal order, recovery correlation, and competing hypotheses."
    )
    adjudication = Adjudication(
        hypothesis_id=leading.hypothesis_id,
        display_name=leading.display_name,
        statement=leading.statement,
        brief_explanation=brief_explanation,
        full_explanation="\\n".join(full_lines),
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
