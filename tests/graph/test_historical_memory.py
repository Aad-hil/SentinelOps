from types import SimpleNamespace

from graph.investigation import _build_historical_memory_node


class FakeHistoricalRepository:
    def __init__(self):
        self.queries = []

    def search(self, query, *, limit):
        self.queries.append((query, limit))
        return [
            SimpleNamespace(
                score=0.81,
                payload={
                    "incident_id": "INC-002",
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
        ]


def make_state():
    incident = SimpleNamespace(
        incident_id="INC-001",
        title="Database connection pool exhaustion",
        description="Database connections were exhausted and requests failed.",
        service="orders",
        severity="HIGH",
    )
    return {
        "incident_id": "INC-001",
        "incident_summary": incident.description,
        "evidence": SimpleNamespace(incident=incident),
    }


def test_historical_memory_node_populates_state_without_becoming_live_evidence():
    repository = FakeHistoricalRepository()
    node = _build_historical_memory_node(repository)
    update = node(make_state())

    assert [match.incident_id for match in update["historical_incidents"]] == ["INC-002"]
    assert update["historical_incidents"][0].score == 0.81
    assert "historical memory retrieved 1" in update["messages"][0].lower()
    # One extra candidate is requested so the current incident can be excluded safely.
    assert repository.queries[0][1] == 4
