from agents.redshift_hypotheses import REDSHIFT_HYPOTHESES, get_redshift_hypothesis
from simulator.redshift import build_all_redshift_incidents, build_redshift_incident, redshift_case_ids
from simulator.evidence import build_evidence_bundle


def test_redshift_hypothesis_catalogue_has_twelve_unique_candidates():
    ids = [item.hypothesis_id for item in REDSHIFT_HYPOTHESES]
    assert len(ids) == 12
    assert len(set(ids)) == 12
    assert ids == [f"RSH{number}" for number in range(1, 13)]


def test_redshift_hypotheses_define_three_causal_stages():
    for item in REDSHIFT_HYPOTHESES:
        assert item.trigger_signals
        assert item.mechanism_signals
        assert item.impact_signals
        assert item.evidence_sources


def test_redshift_catalogue_lookup_is_explicit():
    assert get_redshift_hypothesis("RSH1").name == "WLM Queue Contention"


def test_redshift_simulator_builds_twelve_deterministic_cases():
    first = build_all_redshift_incidents()
    second = build_all_redshift_incidents()
    assert len(first) == 12
    assert redshift_case_ids() == tuple(f"RS-{number:03d}" for number in range(1, 13))
    assert [item.incident.incident_id for item in first] == list(redshift_case_ids())
    assert first == second


def test_redshift_scenarios_are_explicitly_scoped_to_amazon_redshift():
    for scenario in build_all_redshift_incidents():
        assert scenario.incident.service == "amazon-redshift"
        assert scenario.metrics
        assert scenario.logs
        assert scenario.deployments
        assert scenario.traces
        assert scenario.ground_truth.root_cause


def test_redshift_agent_evidence_does_not_expose_answer_key():
    scenario = build_redshift_incident("RS-001")
    evidence = build_evidence_bundle(
        incident=scenario.incident,
        logs=scenario.logs,
        metrics=scenario.metrics,
        deployments=scenario.deployments,
        traces=scenario.traces,
    )
    assert not hasattr(evidence, "ground_truth")
    assert evidence.incident.incident_id == "RS-001"
