import pytest

from simulator.__main__ import build_parser, run_investigation


def test_cli_accepts_redshift_incident_ids_only():
    parser = build_parser()
    assert parser.parse_args(["--incident-id", "RS-001"]).incident_id == "RS-001"
    with pytest.raises(SystemExit):
        parser.parse_args(["--incident-id", "INC-002"])


@pytest.mark.parametrize("incident_id", ["RS-001", "RS-012"])
def test_run_redshift_investigation(incident_id, monkeypatch):
    monkeypatch.setenv("SENTINELOPS_CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("SENTINELOPS_RAG_ENABLED", "false")
    state = run_investigation(incident_id)
    assert state["incident_id"] == incident_id
    assert len(state["hypotheses"]) == 12
    assert {item.hypothesis_id for item in state["hypotheses"]} == {
        f"RSH{number}" for number in range(1, 13)
    }
    assert state["adjudication"] is not None
    assert state["safety_decision"] is not None
    assert state["investigation_status"] in {"complete", "awaiting_human_approval"}
