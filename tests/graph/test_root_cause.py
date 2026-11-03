from types import SimpleNamespace

import pytest

from agents.deployment import run_deployment_agent
from agents.root_cause import generate_hypotheses
from agents.telemetry import run_telemetry_agent
from simulator.redshift import build_redshift_evidence_bundle


def _prepared_state(incident_id: str) -> dict:
    evidence = build_redshift_evidence_bundle(incident_id)
    state = {
        "incident_id": incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }
    state.update(run_telemetry_agent(state))
    state.update(run_deployment_agent(state))
    return state


def test_root_cause_generates_only_redshift_hypotheses():
    hypotheses = generate_hypotheses(_prepared_state("RS-001"))

    assert len(hypotheses) == 12
    assert {item.hypothesis_id for item in hypotheses} == {
        f"RSH{number}" for number in range(1, 13)
    }
    assert all(item.hypothesis_id.startswith("RSH") for item in hypotheses)


def test_root_cause_hypotheses_are_sorted_by_confidence():
    hypotheses = generate_hypotheses(_prepared_state("RS-001"))
    confidences = [item.confidence for item in hypotheses]

    assert confidences == sorted(confidences, reverse=True)


def test_root_cause_agent_uses_evidence_without_ground_truth():
    state = _prepared_state("RS-001")
    hypotheses = generate_hypotheses(state)

    assert "ground_truth" not in state
    assert not hasattr(state["evidence"], "ground_truth")
    assert all(not hasattr(item, "ground_truth") for item in hypotheses)


def test_root_cause_rejects_non_redshift_incidents():
    state = {
        "evidence": SimpleNamespace(
            incident=SimpleNamespace(service="some-other-service")
        )
    }

    with pytest.raises(ValueError, match="Amazon Redshift incidents only"):
        generate_hypotheses(state)
