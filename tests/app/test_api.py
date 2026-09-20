from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_investigation_returns_stable_contract() -> None:
    response = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-002"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-002"
    assert payload["status"] in {"complete", "awaiting_human_approval"}
    assert payload["root_cause"]["hypothesis_id"] == "H1"
    assert payload["root_cause"]["confidence"] == 0.95
    assert payload["root_cause"]["alternative_gaps"] == []
    assert payload["hypotheses"]
    assert payload["hypotheses"][0]["causal_relationships"]
    assert payload["evidence"]
    assert payload["recovery_plan"] is not None
    assert payload["safety_decision"] is not None
    assert "decision" in payload["safety_decision"]


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
