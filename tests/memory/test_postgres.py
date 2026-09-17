from datetime import datetime, timezone

from memory.models import IncidentMemory
from memory.postgres import PostgresIncidentMemoryRepository


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class FakeConnection:
    def __init__(self, rows=None):
        self.cursor_instance = FakeCursor(rows)
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True


def make_memory() -> IncidentMemory:
    return IncidentMemory(
        incident_id="INC-002",
        service="github-web",
        severity="HIGH",
        title="Primary database saturation after deployment",
        description="Database saturation caused elevated update errors.",
        root_cause_hypothesis_id="H1",
        root_cause_statement="A deployment caused primary database saturation.",
        root_cause_confidence=0.95,
        resolution_summary="The problematic deployment was rolled back.",
        recovery_action="Rollback deployment and verify error rate recovery.",
        created_at=datetime(2025, 1, 9, 1, 26, tzinfo=timezone.utc),
        completed_at=datetime(2025, 1, 9, 1, 56, tzinfo=timezone.utc),
    )


def test_initialize_creates_schema():
    connection = FakeConnection()
    repository = PostgresIncidentMemoryRepository(lambda: connection)

    repository.initialize()

    assert "CREATE TABLE IF NOT EXISTS incident_memory" in connection.cursor_instance.executed[0][0]
    assert connection.committed is True


def test_save_upserts_incident_memory():
    connection = FakeConnection()
    repository = PostgresIncidentMemoryRepository(lambda: connection)
    memory = make_memory()

    repository.save(memory)

    sql, params = connection.cursor_instance.executed[0]
    assert "INSERT INTO incident_memory" in sql
    assert params["incident_id"] == "INC-002"
    assert params["root_cause_confidence"] == 0.95
    assert connection.committed is True


def test_get_returns_incident_memory():
    memory = make_memory()
    row = (
        memory.incident_id,
        memory.service,
        memory.severity,
        memory.title,
        memory.description,
        memory.root_cause_hypothesis_id,
        memory.root_cause_statement,
        memory.root_cause_confidence,
        memory.resolution_summary,
        memory.recovery_action,
        memory.created_at,
        memory.completed_at,
    )
    connection = FakeConnection([row])
    repository = PostgresIncidentMemoryRepository(lambda: connection)

    result = repository.get("INC-002")

    assert result == memory


def test_get_returns_none_for_unknown_incident():
    connection = FakeConnection()
    repository = PostgresIncidentMemoryRepository(lambda: connection)

    assert repository.get("INC-404") is None


def test_list_all_maps_rows():
    first = make_memory()
    second = IncidentMemory(
        incident_id="INC-001",
        service="checkout",
        severity="MEDIUM",
        title="Database connection pool exhaustion",
        description="The service exhausted its database connection pool.",
        root_cause_hypothesis_id="H1",
        root_cause_statement="A connection leak exhausted the pool.",
        root_cause_confidence=0.9,
        resolution_summary="Connections were recycled.",
        recovery_action="Restart the affected service and verify pool health.",
    )
    rows = [
        (
            first.incident_id,
            first.service,
            first.severity,
            first.title,
            first.description,
            first.root_cause_hypothesis_id,
            first.root_cause_statement,
            first.root_cause_confidence,
            first.resolution_summary,
            first.recovery_action,
            first.created_at,
            first.completed_at,
        ),
        (
            second.incident_id,
            second.service,
            second.severity,
            second.title,
            second.description,
            second.root_cause_hypothesis_id,
            second.root_cause_statement,
            second.root_cause_confidence,
            second.resolution_summary,
            second.recovery_action,
            second.created_at,
            second.completed_at,
        ),
    ]
    connection = FakeConnection(rows)
    repository = PostgresIncidentMemoryRepository(lambda: connection)

    result = repository.list_all()

    assert result == [first, second]
