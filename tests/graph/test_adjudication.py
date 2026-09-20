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

    by_id = {hypothesis.hypothesis_id: hypothesis for hypothesis in hypotheses}
    assert by_id["H1"].confidence > by_id["H2"].confidence
    assert by_id["H2"].status == "insufficient_evidence"
    assert by_id["H3"].status == "insufficient_evidence"


def test_adjudication_does_not_use_ground_truth():
    evidence = build_incident_002_evidence()
    result = build_investigation_graph().invoke({"evidence": evidence})

    assert "ground_truth" not in result
    assert "ground_truth" not in result["adjudication"].rationale.lower()


def test_adjudication_handles_empty_hypotheses():
    hypotheses, adjudication = adjudicate_hypotheses({"evidence_items": []})

    assert hypotheses == []
    assert adjudication is None

def test_adjudication_preserves_causal_relationships():
    evidence = build_incident_002_evidence()
    result = build_investigation_graph().invoke({"evidence": evidence})

    h1 = next(h for h in result["hypotheses"] if h.hypothesis_id == "H1")

    assert {r.role for r in h1.causal_relationships} == {
        "trigger",
        "mechanism",
        "impact",
    }
    assert all(r.hypothesis_id == "H1" for r in h1.causal_relationships)
    assert all(r.rationale for r in h1.causal_relationships)

