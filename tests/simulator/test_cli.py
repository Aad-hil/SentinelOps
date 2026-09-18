from simulator.__main__ import build_parser, run_investigation


def test_cli_requires_incident_id():
    parser = build_parser()
    args = parser.parse_args(["--incident-id", "INC-002"])
    assert args.incident_id == "INC-002"


def test_run_investigation_incident_002():
    state = run_investigation("INC-002")

    assert state["incident_id"] == "INC-002"
    assert state["investigation_status"] == "awaiting_human_approval"
    assert state["plan"]
    assert {finding.agent for finding in state["findings"]} >= {
        "telemetry",
        "knowledge",
        "deployment",
        "root_cause",
        "critic",
        "adjudication",
        "recovery",
        "safety",
    }
    assert len(state["hypotheses"]) == 3
    assert state["critique"] is not None
    assert state["adjudication"] is not None
    assert state["evidence_items"]


def test_run_investigation_incident_001():
    state = run_investigation("INC-001")
    assert state["incident_id"] == "INC-001"
    assert state["investigation_status"] == "complete"
