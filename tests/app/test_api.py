import os

os.environ.setdefault("SENTINELOPS_CHECKPOINT_BACKEND", "memory")

import pytest
from fastapi.testclient import TestClient

from app.api import _CHECKPOINTER, _GRAPH, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_incident_checkpoint() -> None:
    """Keep API HITL tests isolated while reusing the benchmark incident."""
    _CHECKPOINTER.delete_thread("INC-002")


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_is_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "SentinelOps" in response.text
    assert "INC-002" in response.text
    assert "Approve Recovery" in response.text


def test_investigation_stops_at_human_approval() -> None:
    response = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-002"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-002"
    assert payload["status"] == "awaiting_human_approval"
    assert payload["approval_status"] == "pending"
    assert payload["approval_required"] is True
    assert payload["root_cause"]["hypothesis_id"] == "H1"
    assert payload["root_cause"]["confidence"] == 0.95
    assert payload["hypotheses"]
    assert payload["evidence"]
    assert payload["recovery_plan"] is not None
    assert payload["safety_decision"] is not None


def test_approval_resumes_investigation_without_restarting() -> None:
    started = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-002"},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "awaiting_human_approval"

    response = client.post(
        "/api/v1/investigations/INC-002/approval",
        json={"approved": True, "reviewer": "Aadhil"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-002"
    assert payload["status"] == "approved_for_execution"
    assert payload["approval_status"] == "approved"
    assert payload["approval_required"] is False
    assert payload["root_cause"]["hypothesis_id"] == "H1"
    assert payload["recovery_plan"] is not None



def test_rejection_blocks_investigation() -> None:
    started = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-002"},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "awaiting_human_approval"

    response = client.post(
        "/api/v1/investigations/INC-002/approval",
        json={"approved": False, "reviewer": "Aadhil"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-002"
    assert payload["status"] == "blocked"
    assert payload["approval_status"] == "rejected"
    assert payload["approval_required"] is False

def test_approval_requires_pending_investigation() -> None:
    config = {"configurable": {"thread_id": "INC-002"}}

    _GRAPH.update_state(
        config,
        {
            "investigation_status": "complete",
            "approval_required": False,
        },
    )

    response = client.post(
        "/api/v1/investigations/INC-002/approval",
        json={"approved": True, "reviewer": "Aadhil"},
    )

    assert response.status_code == 409


def test_openapi_exposes_typed_response_schema() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()["components"]["schemas"]["InvestigationResponse"]
    assert schema["properties"]["root_cause"]["anyOf"]
    assert "AdjudicationResponse" in str(schema)
    assert "dict" not in str(schema["properties"]["hypotheses"])


def test_unknown_incident_returns_404() -> None:
    response = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-999"},
    )


    assert response.status_code == 404
