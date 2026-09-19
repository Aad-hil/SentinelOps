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
