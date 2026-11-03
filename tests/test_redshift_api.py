"""Local API contracts for the current Redshift investigation flow."""
import importlib
import pytest
from fastapi import HTTPException
from langgraph.checkpoint.memory import MemorySaver
from graph.investigation import build_investigation_graph

@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("SENTINELOPS_CHECKPOINT_BACKEND", "memory")
    monkeypatch.setenv("SENTINELOPS_RAG_ENABLED", "false")
    module = importlib.import_module("app.api")
    checkpoint = MemorySaver()
    monkeypatch.setattr(module, "_CHECKPOINTER", checkpoint)
    monkeypatch.setattr(module, "_GRAPH", build_investigation_graph(checkpointer=checkpoint))
    return module

def test_health_and_catalog(api):
    assert api.health() == {"status": "ok"}
    assert api.dashboard().path.name == "index.html"
    incidents = api.list_incidents()
    assert len(incidents) == 12
    assert all(item["service"] == "amazon-redshift" for item in incidents)

def test_investigation_persistence_and_deletion(api):
    request = api.InvestigationRequest(incident_id="RS-001")
    result = api.investigate(request)
    assert result.root_cause.hypothesis_id == "RSH1"
    assert result.safety_decision.decision == "blocked"
    assert result.approval_required is False
    assert result.evidence and result.hypotheses
    assert api.get_incident("RS-001").incident_id == "RS-001"
    assert api.investigate(request).status == result.status
    assert api.delete_incident("RS-001")["status"] == "deleted"
    with pytest.raises(HTTPException) as exc:
        api.get_incident("RS-001")
    assert exc.value.status_code == 404

def test_invalid_incident_and_approval_guard(api):
    with pytest.raises(HTTPException) as exc:
        api.investigate(api.InvestigationRequest(incident_id="INC-001"))
    assert exc.value.status_code == 404
    api.investigate(api.InvestigationRequest(incident_id="RS-001"))
    with pytest.raises(HTTPException) as exc:
        api.approve_investigation("RS-001", api.ApprovalRequest(approved=True, reviewer="operator"))
    assert exc.value.status_code == 409
