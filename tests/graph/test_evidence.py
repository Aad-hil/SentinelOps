from datetime import datetime, timezone

from graph.evidence import EvidenceItem, append_evidence
from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence


def test_evidence_item_validates_required_fields_and_relevance():
    timestamp = datetime.now(timezone.utc)
    item = EvidenceItem(
        source="metric:db_cpu",
        evidence_type="metric",
        observation="db_cpu=98",
        timestamp=timestamp,
        relevance=0.9,
        agent="telemetry",
    )
    assert item.source == "metric:db_cpu"
    assert item.relevance == 0.9


def test_append_evidence_deduplicates_exact_items():
    item = EvidenceItem("log:1", "log", "database saturated", relevance=0.8)
    assert append_evidence([item], [item]) == [item]


def test_graph_accumulates_evidence_from_all_specialists():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()
    result = graph.invoke({"evidence": evidence})

    items = result["evidence_items"]
    assert items
    assert {item.agent for item in items} == {"telemetry", "knowledge", "deployment"}
    assert {item.evidence_type for item in items} >= {
        "log",
        "metric",
        "trace",
        "deployment",
        "deployment_change",
        "knowledge_reference",
    }
