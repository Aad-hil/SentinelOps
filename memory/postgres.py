from __future__ import annotations

import os
from collections.abc import Callable

import psycopg

from memory.models import IncidentMemory


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS incident_memory (
    incident_id TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    root_cause_hypothesis_id TEXT,
    root_cause_statement TEXT,
    root_cause_confidence DOUBLE PRECISION,
    resolution_summary TEXT,
    recovery_action TEXT,
    created_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
)
"""

UPSERT_SQL = """
INSERT INTO incident_memory (
    incident_id,
    service,
    severity,
    title,
    description,
    root_cause_hypothesis_id,
    root_cause_statement,
    root_cause_confidence,
    resolution_summary,
    recovery_action,
    created_at,
    completed_at
) VALUES (
    %(incident_id)s,
    %(service)s,
    %(severity)s,
    %(title)s,
    %(description)s,
    %(root_cause_hypothesis_id)s,
    %(root_cause_statement)s,
    %(root_cause_confidence)s,
    %(resolution_summary)s,
    %(recovery_action)s,
    %(created_at)s,
    %(completed_at)s
)
ON CONFLICT (incident_id) DO UPDATE SET
    service = EXCLUDED.service,
    severity = EXCLUDED.severity,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    root_cause_hypothesis_id = EXCLUDED.root_cause_hypothesis_id,
    root_cause_statement = EXCLUDED.root_cause_statement,
    root_cause_confidence = EXCLUDED.root_cause_confidence,
    resolution_summary = EXCLUDED.resolution_summary,
    recovery_action = EXCLUDED.recovery_action,
    created_at = EXCLUDED.created_at,
    completed_at = EXCLUDED.completed_at
"""

SELECT_ONE_SQL = """
SELECT
    incident_id,
    service,
    severity,
    title,
    description,
    root_cause_hypothesis_id,
    root_cause_statement,
    root_cause_confidence,
    resolution_summary,
    recovery_action,
    created_at,
    completed_at
FROM incident_memory
WHERE incident_id = %s
"""

SELECT_ALL_SQL = """
SELECT
    incident_id,
    service,
    severity,
    title,
    description,
    root_cause_hypothesis_id,
    root_cause_statement,
    root_cause_confidence,
    resolution_summary,
    recovery_action,
    created_at,
    completed_at
FROM incident_memory
ORDER BY completed_at DESC NULLS LAST, incident_id
"""

ConnectionFactory = Callable[[], psycopg.Connection]


def _connection_factory_from_env() -> ConnectionFactory:
    """Build a PostgreSQL connection factory from SentinelOps environment settings."""
    kwargs = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "sentinelops"),
        "user": os.getenv("POSTGRES_USER", "sentinelops"),
    }
    password = os.getenv("POSTGRES_PASSWORD")
    if password:
        kwargs["password"] = password

    def connect() -> psycopg.Connection:
        return psycopg.connect(**kwargs)

    return connect


def _row_to_memory(row: tuple) -> IncidentMemory:
    return IncidentMemory(
        incident_id=row[0],
        service=row[1],
        severity=row[2],
        title=row[3],
        description=row[4],
        root_cause_hypothesis_id=row[5],
        root_cause_statement=row[6],
        root_cause_confidence=row[7],
        resolution_summary=row[8],
        recovery_action=row[9],
        created_at=row[10],
        completed_at=row[11],
    )


class PostgresIncidentMemoryRepository:
    """Persist completed incident memories in PostgreSQL."""

    def __init__(self, connection_factory: ConnectionFactory | None = None) -> None:
        self._connect = connection_factory or _connection_factory_from_env()

    def initialize(self) -> None:
        """Create the incident-memory table if it does not already exist."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_TABLE_SQL)
            connection.commit()

    def save(self, memory: IncidentMemory) -> None:
        """Insert or update one incident memory."""
        params = {
            "incident_id": memory.incident_id,
            "service": memory.service,
            "severity": memory.severity,
            "title": memory.title,
            "description": memory.description,
            "root_cause_hypothesis_id": memory.root_cause_hypothesis_id,
            "root_cause_statement": memory.root_cause_statement,
            "root_cause_confidence": memory.root_cause_confidence,
            "resolution_summary": memory.resolution_summary,
            "recovery_action": memory.recovery_action,
            "created_at": memory.created_at,
            "completed_at": memory.completed_at,
        }
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(UPSERT_SQL, params)
            connection.commit()

    def get(self, incident_id: str) -> IncidentMemory | None:
        """Return one incident memory by ID, or None when it does not exist."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(SELECT_ONE_SQL, (incident_id,))
                row = cursor.fetchone()
        return _row_to_memory(row) if row else None

    def list_all(self) -> list[IncidentMemory]:
        """Return incident memories ordered by completion time."""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(SELECT_ALL_SQL)
                rows = cursor.fetchall()
        return [_row_to_memory(row) for row in rows]
