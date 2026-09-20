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
    statement: str
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    confidence: float
    status: str = "candidate"
    causal_score: float = 0.0
    causal_evidence: tuple[str, ...] = ()
    causal_relationships: tuple[CausalEvidenceRelationship, ...] = ()


# Generic causal patterns; these are not benchmark ground truth.
_HYPOTHESES = (
    ("H1", "A recent deployment introduced a database-impacting change that caused primary database saturation.",
     ("deployment", "query", "database", "cpu", "saturation")),
    ("H2", "A traffic or request-volume spike overloaded database capacity, reduced available headroom, and caused the observed errors.",
     ("traffic", "request", "load", "queue", "request_rate")),
    ("H3", "A network or downstream dependency problem increased request latency and caused failures.",
     ("network", "downstream", "latency", "timeout")),
    ("H4", "A primary database connection-capacity problem exhausted available connections and caused request failures.",
     ("connection", "pool", "capacity", "connection_utilization", "connection_errors")),
    ("H5", "A database query regression or slow query caused lock contention, resource pressure, or unusually slow queries.",
     ("query", "lock", "contention", "query_latency", "slow")),
    ("H6", "A schema or database migration overlapped with peak query workload and caused database resource contention and connection saturation.",
     ("schema", "migration", "alter", "contention")),
    ("H7", "A database primary failure, version/configuration issue, or unstable failover caused service disruption.",
     ("primary", "failover", "crash", "health")),
    ("H8", "A database migration or configuration, version, or permission regression caused database insert/write operations to fail.",
     ("permission", "permissions", "configuration", "version", "insert")),
    ("H9", "A new API data shape caused an expensive database write transaction and query/resource pressure, resulting in latency and timeouts.",
     ("write", "transaction", "expensive", "write_latency", "timeout")),
    ("H10", "High request volume amplified database queries, causing database replication lag and stale or unavailable replica data.",
     ("replication", "lag", "replica")),
    ("H11", "An infrastructure or data-store upgrade introduced resource contention, degraded database queries, and caused dependent timeouts.",
     ("upgrade", "data-store", "resource_contention", "version")),
    ("H12", "An inefficient database query triggered by API or background workload caused queue or webhook backlog and latency.",
     ("queue", "background", "webhook", "backlog", "inefficient")),
)

# Each causal pattern is evaluated as trigger -> mechanism -> impact.
# A hypothesis receives causal support only when evidence covers multiple
# stages of that chain in chronological order; keyword presence alone is not
# treated as causal proof.
_CAUSAL_REQUIREMENTS = {
    "H1": (("deployment", "change", "release"), ("query", "database", "db"), ("saturation", "cpu", "error")),
    "H2": (("traffic", "request", "load", "rate"), ("overload", "capacity", "queue", "headroom", "saturation", "cpu", "pressure"), ("error", "latency", "timeout")),
    "H3": (("network", "downstream", "dependency"), ("timeout", "latency", "failure"), ("error", "request")),
    "H4": (("connection", "pool", "capacity"), ("exhaust", "wait", "queue"), ("error", "failure", "latency")),
    "H5": (("query change", "slow query", "long-running query"), ("lock", "contention", "slow", "resource pressure"), ("latency", "cpu", "error")),
    "H6": (("schema", "migration", "alter"), ("contention", "resource", "load", "connection"), ("latency", "error", "connection")),
    "H7": (("primary", "crash", "failure"), ("failover", "recovery", "unstable"), ("error", "outage", "health")),
    "H8": (("configuration", "version", "migration", "missing permission", "permissions missing", "permission denied", "permission change"), ("permission", "config", "insert", "write"), ("error", "failure")),
    "H9": (("write transaction", "new data shape", "expensive write"), ("expensive", "cpu", "resource"), ("latency", "timeout", "error")),
    "H10": (("replication", "replica", "request"), ("lag", "replication"), ("stale", "unavailable", "latency")),
    "H11": (("upgrade", "version", "data-store"), ("contention", "resource", "pressure"), ("latency", "timeout", "error")),
    "H12": (("background", "queue", "api", "request"), ("inefficient", "query", "backlog"), ("queue", "webhook", "latency", "error")),
}


def _evidence_text(item: EvidenceItem) -> str:
    return (item.source + " " + item.observation).lower()


def _matches_signal(item: EvidenceItem, signal: str) -> bool:
    text = _evidence_text(item)
    normalized = signal.lower().replace("_", " ")
    return signal.lower() in text or normalized in text


def _timestamp_key(item: EvidenceItem) -> datetime:
    """Return a comparable UTC timestamp for aware or naive evidence times."""
    timestamp = item.timestamp
    if timestamp is None:
        return datetime.max.replace(tzinfo=timezone.utc)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _causal_chain(
    hypothesis_id: str,
    items: list[EvidenceItem],
) -> tuple[float, tuple[str, ...]]:
    """Measure whether evidence supports a chronological causal chain."""
    requirements = _CAUSAL_REQUIREMENTS[hypothesis_id]
    stages: list[list[EvidenceItem]] = []

    for role_index, signals in enumerate(requirements):
        matches = [
            item for item in items
            if any(_matches_signal(item, signal) for signal in signals)
            and not (
                role_index < 2
                and (
                    item.evidence_type == "recovery"
                    or any(
                        term in _evidence_text(item)
                        for term in ("rollback", "restart", "recovery", "throttle", "protect")
                    )
                )
            )
        ]
        stages.append(matches)

    covered = sum(bool(stage) for stage in stages)
    if covered == 0:
        return 0.0, ()

    ordered = True
    previous = None
    selected: list[EvidenceItem] = []
    for stage in stages:
        if not stage:
            ordered = False
            continue

        if previous is None:
            candidate = min(stage, key=_timestamp_key)
        else:
            later = [item for item in stage if _timestamp_key(item) >= previous]
            candidate = min(later, key=_timestamp_key) if later else None
            if candidate is None:
                ordered = False
                continue

        selected.append(candidate)
        previous = _timestamp_key(candidate)

    score = covered / len(stages)
    if ordered and covered == len(stages):
        score = 1.0

    return round(score, 3), tuple(item.source for item in selected if item is not None)

def _causal_relationships(
    hypothesis_id: str,
    items: list[EvidenceItem],
) -> tuple[CausalEvidenceRelationship, ...]:
    """Map evidence to trigger, mechanism, and impact roles for a hypothesis."""
    role_names = ("trigger", "mechanism", "impact")
    requirements = _CAUSAL_REQUIREMENTS[hypothesis_id]
    relationships: list[CausalEvidenceRelationship] = []

    for role_index, signals in enumerate(requirements):
        matches = [
            item for item in items
            if any(_matches_signal(item, signal) for signal in signals)
            and not (
                role_index < 2
                and (
                    item.evidence_type == "recovery"
                    or any(
                        term in _evidence_text(item)
                        for term in ("rollback", "restart", "recovery", "throttle", "protect")
                    )
                )
            )
        ]
        for item in matches:
            strength = 0.55
            if item.evidence_type in {"deployment", "deployment_change"} and role_index == 0:
                strength += 0.15
            matched_signals = tuple(
                signal for signal in signals if _matches_signal(item, signal)
            )
            relationships.append(
                CausalEvidenceRelationship(
                    source=item.source,
                    role=role_names[role_index],
                    hypothesis_id=hypothesis_id,
                    strength=round(min(1.0, strength), 3),
                    rationale=(
                        f"Evidence matches {role_names[role_index]} signals "
                        f"for {hypothesis_id}: {', '.join(matched_signals)}."
                    ),
                )
            )

    return tuple(relationships)


def _hypothesis_identity_strength(
    hypothesis_id: str,
    items: list[EvidenceItem],
) -> float:
    """Measure evidence for signals that distinguish a hypothesis from peers."""
    identity_signals = {
        "H1": ("deployment", "query"),
        "H2": ("traffic", "request_rate", "load"),
        "H3": ("network", "downstream", "dependency"),
        "H4": ("connection", "pool", "connection_errors"),
        "H5": ("lock", "contention", "slow", "query_change"),
        "H6": ("schema", "migration", "alter"),
        "H7": ("crash", "failover", "database_version", "configuration"),
        "H8": ("permission", "permissions", "migration", "configuration"),
        "H9": ("expensive", "transaction", "write_latency"),
        "H10": ("replication", "lag", "token"),
        "H11": ("upgrade", "data-store", "version"),
        "H12": ("inefficient", "background", "queue", "webhook"),
    }[hypothesis_id]
    matched = sum(
        any(_matches_signal(item, signal) for item in items)
        for signal in identity_signals
    )
    return min(1.0, matched / 2.0)


def _trigger_evidence_strength(
    hypothesis_id: str,
    items: list[EvidenceItem],
) -> float:
    """Prefer hypotheses whose trigger is directly evidenced by a change record.

    Causal-chain completeness can tie a specific trigger hypothesis with a
    broader symptom hypothesis. When that happens, evidence from deployment or
    change records is stronger trigger evidence than downstream symptoms alone.
    This keeps ranking evidence-driven without hard-coding incident IDs.
    """
    requirements = _CAUSAL_REQUIREMENTS[hypothesis_id]
    trigger_signals = requirements[0]
    trigger_items = [
        item
        for item in items
        if any(_matches_signal(item, signal) for signal in trigger_signals)
    ]
    if not trigger_items:
        return 0.0

    # A change record is strong trigger evidence only when the change itself
    # contains the hypothesis trigger. Recovery/mitigation changes such as a
    # restart, rollback, or throttling action should not be mistaken for the
    # incident trigger.
    # A generic deployment record is not, by itself, proof of a deployment-caused
    # incident. Require a hypothesis-specific trigger signal in the observation
    # rather than matching the generic "deployment" signal from the evidence
    # source label.
    direct_change_items = [
        item
        for item in trigger_items
        if item.evidence_type in {"deployment", "deployment_change"}
        and any(
            _matches_signal(item, signal)
            for signal in trigger_signals
            if signal != "deployment"
        )
        and not any(
            term in _evidence_text(item)
            for term in ("restart", "rollback", "recovery", "throttle", "protect")
        )
    ]
    if direct_change_items:
        return 1.0

    # Telemetry is more direct than retrieved knowledge: a request-rate metric
    # or an observed trace is evidence of what happened, while a runbook is
    # contextual guidance. Keep the distinction bounded so evidence quantity
    # still matters.
    weights = {
        "metric": 0.66,
        "log": 0.66,
        "trace": 0.66,
        "recovery": 0.45,
        "knowledge": 0.33,
        "knowledge_reference": 0.25,
    }
    return min(
        0.66,
        max(weights.get(item.evidence_type, 0.50) for item in trigger_items),
    )


def _mechanism_evidence_strength(
    hypothesis_id: str,
    items: list[EvidenceItem],
) -> float:
    """Measure evidence for the hypothesis-specific middle causal mechanism."""
    requirements = _CAUSAL_REQUIREMENTS[hypothesis_id]
    mechanism_signals = requirements[1]
    matches = [
        item
        for item in items
        if any(_matches_signal(item, signal) for signal in mechanism_signals)
    ]
    if not matches:
        return 0.0

    specific_terms = {
        "H1": ("query",),
        "H2": ("overload", "capacity", "cpu"),
        "H3": ("downstream", "network"),
        "H4": ("exhaust", "pool"),
        "H5": ("lock", "slow"),
        "H6": ("schema", "migration"),
        "H7": ("failover", "crash", "unstable"),
        "H8": ("permission", "insert"),
        "H9": ("expensive", "transaction"),
        "H10": ("replication", "lag"),
        "H11": ("upgrade", "version"),
        "H12": ("inefficient", "backlog"),
    }.get(hypothesis_id, ())
    specific_matches = [
        item for item in matches
        if any(_matches_signal(item, signal) for signal in specific_terms)
    ]
    if specific_matches:
        return 1.0
    return min(len(matches) / 3.0, 0.66)


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


def _incident_context_trigger_strength(
    hypothesis_id: str,
    state: InvestigationState,
) -> float:
    """Measure whether the incident summary explicitly describes a hypothesis trigger."""
    incident = state.get("evidence")
    if incident is None:
        return 0.0

    text = f"{incident.incident.title} {incident.incident.description}".lower()
    trigger_signals = _CAUSAL_REQUIREMENTS[hypothesis_id][0]
    matched = sum(signal.lower() in text for signal in trigger_signals)
    return min(1.0, matched / 2.0)


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
        causal_score, causal_evidence = _causal_chain(hypothesis_id, items)
        if causal_evidence:
            supporting_sources = tuple(dict.fromkeys(
                (*[item.source for item in supporting], *causal_evidence)
            ))
        else:
            supporting_sources = tuple(item.source for item in supporting)
        contradiction_penalty = min(len(contradictions) / 4.0, 0.6)
        trigger_strength = max(
            _trigger_evidence_strength(hypothesis_id, items),
            _incident_context_trigger_strength(hypothesis_id, state),
        )
        mechanism_strength = _mechanism_evidence_strength(hypothesis_id, items)
        identity_strength = _hypothesis_identity_strength(hypothesis_id, items)
        causal_relationships = _causal_relationships(hypothesis_id, items)
        identity_penalty = 0.20 * (1.0 - identity_strength)

        # Evidence quantity remains useful, but causal structure has greater
        # weight so a shared symptom cannot outrank a complete causal chain.
        # Small provenance bonuses prefer hypotheses with directly observed
        # trigger and mechanism evidence over generic symptom explanations.
        confidence = max(
            0.0,
            min(
                1.0,
                0.10
                + support_score * 0.35
                + causal_score * 0.55
                + trigger_strength * 0.20
                + mechanism_strength * 0.07
                - contradiction_penalty
                - identity_penalty,
            ),
        )

        hypotheses.append(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                statement=statement,
                supporting_evidence=supporting_sources,
                contradicting_evidence=tuple(item.source for item in contradictions),
                confidence=round(confidence, 3),
                status="supported" if confidence >= 0.6 else "candidate",
                causal_score=causal_score,
                causal_evidence=causal_evidence,
                causal_relationships=causal_relationships,
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
            f"Root Cause Agent evaluated {len(hypotheses)} competing hypotheses with causal-chain scoring."
        ],
        "investigation_status": "hypothesis_evaluation",
    })
    return result
