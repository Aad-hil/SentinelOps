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

def test_mechanism_evidence_strength_rewards_hypothesis_specific_signal():
    from agents.root_cause import _mechanism_evidence_strength

    items = [
        EvidenceItem(
            source="deployment:inc-007-v2",
            evidence_type="deployment",
            observation="new data shape creates an expensive database write transaction",
            timestamp=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="metric:write-latency",
            evidence_type="metric",
            observation="database resource pressure increased",
            timestamp=datetime(2026, 9, 8, 12, 2, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    assert _mechanism_evidence_strength("H9", items) == 1.0
    assert _mechanism_evidence_strength("H5", items) < 1.0

def test_hypothesis_identity_strength_requires_distinguishing_evidence():
    from agents.root_cause import _hypothesis_identity_strength

    items = [
        EvidenceItem(
            source="metric:request-rate",
            evidence_type="metric",
            observation="request rate increased sharply",
            timestamp=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
        EvidenceItem(
            source="metric:db-cpu",
            evidence_type="metric",
            observation="database CPU reached saturation",
            timestamp=datetime(2026, 9, 20, 12, 1, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    assert _hypothesis_identity_strength("H2", items) == 0.5
    assert _hypothesis_identity_strength("H9", items) == 0.0

def test_causal_relationships_assign_trigger_mechanism_and_impact_roles():
    from agents.root_cause import _causal_relationships

    items = [
        EvidenceItem(
            source="deployment:inc-007",
            evidence_type="deployment",
            observation="new data shape creates an expensive write transaction",
            timestamp=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="metric:write-latency",
            evidence_type="metric",
            observation="write latency increased and requests timed out",
            timestamp=datetime(2026, 9, 20, 12, 2, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    relationships = _causal_relationships("H9", items)

    assert {relationship.role for relationship in relationships} == {
        "trigger",
        "mechanism",
        "impact",
    }
    assert all(relationship.hypothesis_id == "H9" for relationship in relationships)
    assert all(0.0 < relationship.strength <= 1.0 for relationship in relationships)

def test_trigger_evidence_strength_does_not_treat_recovery_deployment_as_trigger():
    items = [
        EvidenceItem(
            source="deployment:inc-008-v2",
            evidence_type="deployment",
            observation="database restart reason=connection error recovery",
            timestamp=datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="metric:connection-errors",
            evidence_type="metric",
            observation="db_connection_errors_per_min increased",
            timestamp=datetime(2026, 9, 10, 12, 1, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    assert _trigger_evidence_strength("H4", items) == 0.66
    assert _trigger_evidence_strength("H7", items) < 0.66


def test_trigger_evidence_strength_prefers_direct_migration_over_connection_symptoms():
    items = [
        EvidenceItem(
            source="deployment:inc-015-v2",
            evidence_type="deployment",
            observation="migration=active traffic_window=peak",
            timestamp=datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="metric:connection-utilization",
            evidence_type="metric",
            observation="db_connection_utilization_percent reached 100",
            timestamp=datetime(2026, 9, 15, 12, 1, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    assert _trigger_evidence_strength("H6", items) == 1.0
    assert _trigger_evidence_strength("H4", items) == 0.66

def test_causal_chain_does_not_use_recovery_action_as_root_cause_mechanism():
    items = [
        EvidenceItem(
            source="metric:connection-errors",
            evidence_type="metric",
            observation="primary database connection errors increased",
            timestamp=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
        EvidenceItem(
            source="deployment:restart",
            evidence_type="deployment_change",
            observation="database restart reason=connection error recovery",
            timestamp=datetime(2026, 9, 8, 12, 2, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="log:error",
            evidence_type="log",
            observation="package requests failed",
            timestamp=datetime(2026, 9, 8, 12, 3, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]

    score, _ = _causal_chain("H7", items)

    assert score < 1.0



def test_benchmark_cpu_query_load_prefers_traffic_hypothesis():
    from simulator.benchmark import build_benchmark_incident

    scenario = build_benchmark_incident("INC-003")
    result = build_investigation_graph().invoke({"evidence": scenario})
    assert result["hypotheses"][0].hypothesis_id == "H2"


def test_benchmark_peak_load_prefers_traffic_hypothesis():
    from simulator.benchmark import build_benchmark_incident

    scenario = build_benchmark_incident("INC-010")
    result = build_investigation_graph().invoke({"evidence": scenario})
    assert result["hypotheses"][0].hypothesis_id == "H2"


def test_benchmark_migration_peak_load_prefers_migration_hypothesis():
    from simulator.benchmark import build_benchmark_incident

    scenario = build_benchmark_incident("INC-015")
    result = build_investigation_graph().invoke({"evidence": scenario})
    assert result["hypotheses"][0].hypothesis_id == "H6"
