from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_investigation_returns_structured_result() -> None:
    response = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-002"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_id"] == "INC-002"
    assert payload["status"] in {"complete", "awaiting_human_approval"}
    assert payload["hypotheses"]
    assert payload["evidence"]
    assert payload["root_cause"]["hypothesis_id"] == "H1"
    assert payload["safety_decision"] is not None


def test_unknown_incident_returns_404() -> None:
    response = client.post(
        "/api/v1/investigations",
        json={"incident_id": "INC-999"},
    )

    assert response.status_code == 404
