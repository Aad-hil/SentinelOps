from datetime import datetime, timezone

from agents.root_cause import _causal_chain, _trigger_evidence_strength
from graph.evidence import EvidenceItem
from graph.investigation import build_investigation_graph
from graph.state import InvestigationState
from simulator.scenarios import build_incident_002_evidence


def test_root_cause_agent_generates_competing_hypotheses():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})

    hypotheses = result["hypotheses"]
    assert len(hypotheses) == 12
    assert {hypothesis.hypothesis_id for hypothesis in hypotheses} == {
        "H1", "H2", "H3", "H4", "H5", "H6",
        "H7", "H8", "H9", "H10", "H11", "H12",
    }
    assert all(
        hypothesis.supporting_evidence
        or hypothesis.contradicting_evidence
        or hypothesis.status == "candidate"
        for hypothesis in hypotheses
    )


def test_root_cause_hypotheses_are_sorted_by_confidence():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})
    hypotheses = result["hypotheses"]

    assert [h.confidence for h in hypotheses] == sorted(
        (h.confidence for h in hypotheses), reverse=True
    )


def test_root_cause_agent_does_not_receive_ground_truth():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})

    assert "ground_truth" not in result
    assert all(not hasattr(hypothesis, "ground_truth") for hypothesis in result["hypotheses"])


def test_root_cause_agent_builds_causal_chain_for_incident_002():
    evidence = build_incident_002_evidence()
    result = build_investigation_graph().invoke({"evidence": evidence})

    by_id = {hypothesis.hypothesis_id: hypothesis for hypothesis in result["hypotheses"]}
    h1 = by_id["H1"]

    assert h1.causal_score == 1.0
    assert h1.causal_evidence
    assert h1.causal_evidence[0]
    assert h1.causal_evidence[-1]


def test_causal_chain_handles_mixed_naive_and_aware_timestamps():
    items = [
        EvidenceItem(
            source="deployment:release-1",
            evidence_type="deployment",
            observation="deployment introduced a change",
            timestamp=datetime(2026, 9, 16, 14, 35),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="query:db-1",
            evidence_type="telemetry",
            observation="query caused database pressure",
            timestamp=datetime(2026, 9, 16, 14, 36, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
        EvidenceItem(
            source="metric:db-cpu",
            evidence_type="metric",
            observation="database CPU saturation and error rate increased",
            timestamp=datetime(2026, 9, 16, 14, 37),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    score, evidence = _causal_chain("H1", items)

    assert score == 1.0
    assert evidence == ("deployment:release-1", "query:db-1", "metric:db-cpu")


def test_causal_chain_handles_missing_stages_without_crashing():
    items = [
        EvidenceItem(
            source="deployment:release-1",
            evidence_type="deployment",
            observation="deployment introduced a change",
            timestamp=datetime(2026, 9, 16, 14, 35, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="log:error",
            evidence_type="log",
            observation="request returned error",
            timestamp=datetime(2026, 9, 16, 14, 37, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    score, evidence = _causal_chain("H1", items)

    assert score == 0.667
    assert evidence == ("deployment:release-1", "log:error")

def test_trigger_evidence_strength_prefers_change_records():
    items = [
        EvidenceItem(
            source="deployment:inc-005-v2",
            evidence_type="deployment",
            observation="schema migration is in progress",
            timestamp=datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="metric:db-contention",
            evidence_type="metric",
            observation="database resource contention and connection saturation increased",
            timestamp=datetime(2026, 9, 6, 12, 2, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    assert _trigger_evidence_strength("H6", items) == 1.0
    assert _trigger_evidence_strength("H5", items) < 1.0


def test_trigger_evidence_strength_handles_non_change_trigger_evidence():
    items = [
        EvidenceItem(
            source="metric:request-rate",
            evidence_type="metric",
            observation="request rate increased",
            timestamp=datetime(2026, 9, 6, 12, 1, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    assert 0.0 < _trigger_evidence_strength("H2", items) < 1.0

