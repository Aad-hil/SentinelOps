from types import SimpleNamespace

import pytest

from memory.retrieval import retrieve_historical_incidents


class FakeRepository:
    def __init__(self, points):
        self.points = points
        self.calls = []

    def search(self, query, *, limit):
        self.calls.append((query, limit))
        return self.points[:limit]


def make_point(incident_id="INC-002", score=0.82):
    return SimpleNamespace(
        score=score,
        payload={
            "incident_id": incident_id,
            "title": "Primary database saturation after deployment",
            "service": "github-web",
            "severity": "HIGH",
            "description": "Database saturation caused elevated update errors.",
            "root_cause_statement": "A deployment caused primary database saturation.",
            "root_cause_confidence": 0.95,
            "resolution_summary": "The problematic deployment was rolled back.",
            "recovery_action": "Rollback deployment and verify recovery.",
        },
    )


def test_retrieval_maps_qdrant_payload_to_historical_match():
    repository = FakeRepository([make_point()])

    results = retrieve_historical_incidents(
        repository,
        "database saturation after deployment",
        limit=1,
    )

    assert len(results) == 1
    assert results[0].incident_id == "INC-002"
    assert results[0].score == 0.82
    assert results[0].root_cause_statement.startswith("A deployment")
    assert repository.calls == [("database saturation after deployment", 1)]


def test_retrieval_excludes_current_incident():
    repository = FakeRepository([
        make_point("INC-002", 0.95),
        make_point("INC-001", 0.80),
    ])

    results = retrieve_historical_incidents(
        repository,
        "database saturation",
        limit=1,
        exclude_incident_id="INC-002",
    )

    assert [result.incident_id for result in results] == ["INC-001"]
    assert repository.calls == [("database saturation", 2)]


def test_retrieval_validates_query_and_limit():
    repository = FakeRepository([])

    with pytest.raises(ValueError, match="non-empty"):
        retrieve_historical_incidents(repository, "", limit=1)

    with pytest.raises(ValueError, match="greater than zero"):
        retrieve_historical_incidents(repository, "database", limit=0)
