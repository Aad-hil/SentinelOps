from agents.adjudication import adjudicate_hypotheses
from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence


def test_adjudication_separates_direct_causal_evidence_from_symptoms():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence})
    hypotheses = result["hypotheses"]
    adjudication = result["adjudication"]

    assert adjudication.hypothesis_id == "H1"
    assert adjudication.temporal_support is True
    assert adjudication.causal_support is True
    assert adjudication.recovery_support is True
    assert hypotheses[0].hypothesis_id == "H1"
    assert hypotheses[0].confidence > hypotheses[1].confidence
    assert hypotheses[1].status == "insufficient_evidence"


def test_adjudication_does_not_use_ground_truth():
    evidence = build_incident_002_evidence()
    result = build_investigation_graph().invoke({"evidence": evidence})

    assert "ground_truth" not in result
    assert "ground_truth" not in result["adjudication"].rationale.lower()


def test_adjudication_handles_empty_hypotheses():
    hypotheses, adjudication = adjudicate_hypotheses({"evidence_items": []})

    assert hypotheses == []
    assert adjudication is None
