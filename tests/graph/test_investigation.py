from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence


def test_investigation_graph_collects_from_three_specialist_agents():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke(
        {
            "incident_id": evidence.incident.incident_id,
            "incident_summary": evidence.incident.description,
            "evidence": evidence,
        }
    )

    assert result["investigation_status"] == "complete"
    assert result["plan"] == ["telemetry", "knowledge", "deployment"]
    assert result["completed_tasks"] == ["telemetry", "knowledge", "deployment"]
    assert [finding.agent for finding in result["findings"]] == [
        "telemetry",
        "knowledge",
        "deployment",
    ]


def test_agents_produce_independent_findings():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})
    findings = {finding.agent: finding for finding in result["findings"]}

    assert findings["telemetry"].category == "telemetry"
    assert findings["knowledge"].category == "knowledge"
    assert findings["deployment"].category == "deployment"
    assert findings["telemetry"].summary != findings["deployment"].summary
