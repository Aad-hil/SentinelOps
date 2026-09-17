from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence


def test_critic_agent_challenges_leading_hypothesis():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})

    critique = result["critique"]
    assert critique is not None
    assert critique.hypothesis_id in {"H1", "H2", "H3"}
    assert critique.challenge
    assert critique.confidence >= 0.0
    assert critique.confidence <= 1.0


def test_critic_finding_is_published_to_shared_state():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})
    finding = next(item for item in result["findings"] if item.agent == "critic")

    assert finding.category == "critique"
    assert finding.summary.startswith("Critic challenged")
    assert "critic" in result["completed_tasks"]


def test_investigation_plan_includes_critic_after_root_cause():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})

    expected_plan = [
        "telemetry",
        "knowledge",
        "deployment",
        "root_cause",
        "critic",
        "adjudication",
    ]
    assert result["plan"] == expected_plan
    assert result["completed_tasks"] == expected_plan
    assert result["investigation_status"] == "complete"
