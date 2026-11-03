"""Fresh domain contracts: no legacy incident IDs or external infrastructure."""
import pytest

from simulator.redshift import build_redshift_evidence_bundle, redshift_case_ids
from agents.root_cause import generate_hypotheses


def test_all_twelve_redshift_scenarios_are_available():
    ids = redshift_case_ids()
    assert len(ids) == 12
    assert set(ids) == {f"RS-{i:03d}" for i in range(1, 13)}
    for incident_id in ids:
        bundle = build_redshift_evidence_bundle(incident_id)
        assert bundle.incident.incident_id == incident_id
        assert bundle.incident.service == "amazon-redshift"


def test_hypothesis_engine_requires_redshift_and_ranks_twelve_candidates():
    from agents.telemetry import run_telemetry_agent
    from agents.deployment import run_deployment_agent
    bundle = build_redshift_evidence_bundle("RS-001")
    state = {"incident_id": "RS-001", "evidence": bundle}
    state.update(run_telemetry_agent(state))
    state.update(run_deployment_agent(state))
    hypotheses = generate_hypotheses(state)
    assert len(hypotheses) == 12
    assert hypotheses[0].hypothesis_id == "RSH1"
    assert all(0 <= item.confidence <= 1 for item in hypotheses)


def test_unknown_incident_is_rejected():
    with pytest.raises((KeyError, ValueError)):
        build_redshift_evidence_bundle("INC-001")
