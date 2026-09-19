"""Deterministic synthetic telemetry for the 15-incident evaluation benchmark.

The public incidents are reconstructions: only facts documented by the cited
GitHub availability reports are represented. Logs, metrics, traces, timestamps,
and deployment records are synthetic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from simulator.models import (
    DeploymentEvent,
    GroundTruth,
    Incident,
    IncidentScenario,
    LogEvent,
    MetricPoint,
    TraceSpan,
)


_CASES_PATH = Path(__file__).parents[1] / "evaluation" / "incident_cases.json"


_PROFILES: dict[str, dict] = {
    "database_cpu_query_load": {
        "service": "container-registry",
        "title": "Container Registry database CPU saturation",
        "description": "High-volume package manifest traffic drives a database query beyond its performance envelope.",
        "metric_names": ("db_cpu_percent", "db_query_latency_ms", "package_request_rate"),
        "values": ((52, 61, 72, 84, 93, 97, 98, 96), (45, 52, 75, 120, 260, 510, 820, 740), (120, 135, 180, 260, 410, 560, 610, 540)),
        "deployment_change": {"api_throttle": "permissive", "operation": "Put Manifest"},
        "operation": "PUT /v2/manifests",
    },
    "query_lock_contention": {
        "service": "github-web",
        "title": "Database query lock contention",
        "description": "A frequently used query change increases lock contention and database resource pressure.",
        "metric_names": ("db_lock_wait_ms", "db_query_latency_ms", "db_cpu_percent"),
        "values": ((20, 30, 55, 90, 180, 360, 520, 410), (40, 48, 65, 100, 240, 480, 760, 620), (58, 62, 70, 79, 88, 95, 97, 91)),
        "deployment_change": {"query_change": "frequently-used query", "rollout": "gradual"},
        "operation": "execute changed query",
    },
    "schema_change_database_contention": {
        "service": "database-service",
        "title": "Database contention during schema change",
        "description": "Production query load overlaps with a schema migration and saturates database resources.",
        "metric_names": ("db_connection_utilization_percent", "db_cpu_percent", "db_query_latency_ms"),
        "values": ((62, 68, 76, 88, 96, 100, 100, 94), (55, 61, 69, 78, 89, 95, 97, 92), (45, 50, 70, 110, 260, 500, 760, 620)),
        "deployment_change": {"operation": "schema migration", "status": "in progress"},
        "operation": "ALTER TABLE",
    },
    "maintenance_slow_query": {
        "service": "database-service",
        "title": "Slow query during maintenance",
        "description": "A long-running database query remains active during maintenance and increases database pressure.",
        "metric_names": ("long_running_query_seconds", "db_cpu_percent", "db_query_latency_ms"),
        "values": ((8, 12, 25, 48, 95, 160, 220, 15), (54, 58, 64, 72, 83, 91, 95, 62), (50, 55, 90, 180, 420, 900, 1400, 90)),
        "deployment_change": {"operation": "database maintenance", "query_state": "long-running"},
        "operation": "execute long-running query",
    },
    "expensive_query_write_latency": {
        "service": "permissions-service",
        "title": "Expensive database writes and timeouts",
        "description": "A new API request shape produces expensive database write transactions and timeouts.",
        "metric_names": ("db_write_latency_ms", "db_query_cpu_percent", "request_error_rate_percent"),
        "values": ((70, 90, 130, 220, 410, 700, 980, 760), (45, 50, 60, 72, 84, 93, 97, 88), (0.2, 0.3, 0.5, 1.0, 2.4, 5.1, 8.2, 6.0)),
        "deployment_change": {"api_pattern": "new data shape", "operation": "write transaction"},
        "operation": "INSERT/UPDATE permissions",
    },
    "database_connection_failure": {
        "service": "github-packages",
        "title": "Primary database connection errors",
        "description": "Connection errors to the primary database cause package request latency and failures.",
        "metric_names": ("db_connection_errors_per_min", "db_connection_utilization_percent", "request_latency_ms"),
        "values": ((1, 2, 4, 12, 35, 60, 72, 8), (55, 58, 63, 76, 90, 98, 100, 64), (180, 190, 220, 310, 600, 1100, 1500, 240)),
        "deployment_change": {"action": "database restart", "reason": "connection error recovery"},
        "operation": "connect primary database",
    },
    "database_failover": {
        "service": "repositories",
        "title": "Database primary crash and failover instability",
        "description": "A primary database crash is followed by unstable automated failover.",
        "metric_names": ("db_primary_health", "db_failover_attempts", "request_error_rate_percent"),
        "values": ((1, 1, 1, 0, 0, 0, 0, 1), (0, 0, 0, 1, 2, 3, 4, 4), (0.2, 0.3, 0.4, 8, 18, 24, 31, 2)),
        "deployment_change": {"database_version": "affected version", "configuration": "custom cluster"},
        "operation": "failover primary",
    },
    "peak_load_database_headroom": {
        "service": "git-database",
        "title": "Database resource contention during peak traffic",
        "description": "Peak traffic combines with low database headroom and poorly performing queries.",
        "metric_names": ("request_rate", "db_cpu_percent", "db_headroom_percent"),
        "values": ((100, 110, 125, 150, 190, 240, 280, 210), (60, 64, 72, 82, 91, 97, 99, 88), (40, 36, 28, 18, 9, 3, 1, 12)),
        "deployment_change": {"action": "load throttling", "reason": "protect database headroom"},
        "operation": "write request",
    },
    "database_migration_permissions": {
        "service": "actions",
        "title": "Database migration write failure",
        "description": "Writes switched to a new database cluster fail because required permissions are missing.",
        "metric_names": ("insert_error_rate_percent", "db_write_latency_ms", "request_error_rate_percent"),
        "values": ((0, 0, 0, 18, 45, 60, 55, 2), (70, 72, 75, 210, 500, 760, 700, 90), (0.1, 0.1, 0.2, 3, 8, 12, 10, 0.3)),
        "deployment_change": {"migration": "write traffic switched", "target": "new cluster"},
        "operation": "INSERT row",
    },
    "inefficient_query_background_load": {
        "service": "webhooks",
        "title": "Inefficient query causing background-job backlog",
        "description": "High API volume triggers an inefficient query and causes background-job backlog.",
        "metric_names": ("api_request_rate", "db_query_latency_ms", "queue_depth"),
        "values": ((100, 120, 145, 180, 230, 280, 310, 240), (40, 55, 80, 150, 310, 600, 900, 520), (5, 8, 14, 28, 55, 92, 130, 70)),
        "deployment_change": {"api_pattern": "poorly optimized call", "queue_policy": "protective throttling"},
        "operation": "process webhook",
    },
    "database_replication_lag_query_amplification": {
        "service": "github-apps",
        "title": "Token-request load and database replication lag",
        "description": "A burst of GitHub App token requests amplifies database queries and increases replica lag.",
        "metric_names": ("token_request_rate", "db_replication_lag_seconds", "db_query_latency_ms"),
        "values": ((100, 130, 180, 260, 390, 520, 610, 400), (0.2, 0.3, 0.5, 1.2, 3.0, 7.5, 12.0, 2.0), (40, 45, 60, 90, 180, 350, 520, 140)),
        "deployment_change": {"request_pattern": "token request amplification"},
        "operation": "issue app token",
    },
    "data_store_upgrade_resource_contention": {
        "service": "data-store",
        "title": "Data-store upgrade resource contention",
        "description": "A major-version data-store upgrade produces unexpected resource contention and slow queries.",
        "metric_names": ("resource_contention_percent", "db_query_latency_ms", "request_error_rate_percent"),
        "values": ((20, 25, 35, 55, 75, 91, 96, 60), (45, 48, 60, 100, 240, 620, 980, 220), (0.1, 0.1, 0.2, 0.8, 2.4, 6.0, 8.0, 1.0)),
        "deployment_change": {"upgrade": "major data-store version", "action": "rollback"},
        "operation": "query data store",
    },
    "migration_peak_load_connection_saturation": {
        "service": "database-service",
        "title": "Migration plus peak traffic connection saturation",
        "description": "A database migration overlaps with peak traffic and saturates connection capacity.",
        "metric_names": ("request_rate", "db_connection_utilization_percent", "db_query_latency_ms"),
        "values": ((100, 110, 125, 150, 180, 220, 260, 190), (60, 65, 72, 82, 94, 100, 100, 78), (45, 52, 70, 110, 250, 600, 920, 180)),
        "deployment_change": {"migration": "active", "traffic_window": "peak"},
        "operation": "migration query",
    },
}


def _load_cases() -> list[dict]:
    return json.loads(_CASES_PATH.read_text(encoding="utf-8"))


def _case(incident_id: str) -> dict:
    for case in _load_cases():
        if case["incident_id"] == incident_id:
            return case
    raise KeyError(f"Unknown benchmark incident: {incident_id}")


def _timestamp(incident_id: str) -> datetime:
    number = int(incident_id.split("-")[1])
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(days=number)


def build_benchmark_incident(incident_id: str) -> IncidentScenario:
    """Build a deterministic synthetic scenario for INC-001 through INC-015."""
    case = _case(incident_id)

    if incident_id == "INC-001":
        from simulator.scenarios import build_incident_001

        return build_incident_001()
    if incident_id == "INC-002":
        from simulator.scenarios import build_incident_002

        return build_incident_002()

    category = case["category"]
    profile = _PROFILES[category]
    start = _timestamp(incident_id)

    incident = Incident(
        incident_id=incident_id,
        service=profile["service"],
        severity="HIGH",
        title=case["title"],
        description=profile["description"],
        started_at=start,
        detected_at=start + timedelta(minutes=4),
    )

    deployment = DeploymentEvent(
        timestamp=start - timedelta(minutes=4),
        service=profile["service"],
        version=f"{incident_id.lower()}-v2",
        previous_version=f"{incident_id.lower()}-v1",
        changes=profile["deployment_change"],
    )

    logs = [
        LogEvent(
            timestamp=start - timedelta(minutes=4),
            service=profile["service"],
            level="INFO",
            message="baseline healthy before incident window",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=3),
            service=profile["service"],
            level="INFO",
            message=f"change observed: {', '.join(f'{k}={v}' for k, v in profile['deployment_change'].items())}",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=1),
            service=profile["service"],
            level="WARN",
            message=f"{profile['metric_names'][0]} trending above baseline",
        ),
        LogEvent(
            timestamp=start,
            service=profile["service"],
            level="WARN",
            message=f"{profile['metric_names'][1]} increasing and affecting {profile['operation']}",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=2),
            service=profile["service"],
            level="ERROR",
            message="dependent request latency and error rate increased",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=4),
            service=profile["service"],
            level="ERROR",
            message="incident threshold breached",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=7),
            service=profile["service"],
            level="INFO",
            message=f"mitigation signal observed for {profile['operation']}",
        ),
    ]

    metrics: list[MetricPoint] = []
    for metric_name, values in zip(profile["metric_names"], profile["values"], strict=True):
        for minute, value in enumerate(values):
            metrics.append(
                MetricPoint(
                    timestamp=start + timedelta(minutes=minute),
                    metric_name=metric_name,
                    service=profile["service"],
                    value=float(value),
                )
            )

    traces = []
    for minute in range(8):
        status = "OK" if minute < 4 else "ERROR"
        traces.append(
            TraceSpan(
                timestamp=start + timedelta(minutes=minute),
                trace_id=f"{incident_id.lower()}-trace-{minute:03d}",
                service=profile["service"],
                operation=profile["operation"],
                duration_ms=180 + minute * 170,
                status=status,
            )
        )

    ground_truth = GroundTruth(
        root_cause=case["expected_root_cause"],
        trigger=case["expected_trigger"],
        affected_component=case["expected_affected_component"],
        mitigation=case["expected_mitigation"],
        contributing_factors=tuple(case["required_evidence"]),
    )

    return IncidentScenario(
        incident=incident,
        logs=tuple(logs),
        metrics=tuple(metrics),
        deployments=(deployment,),
        traces=tuple(traces),
        ground_truth=ground_truth,
    )


def build_all_benchmark_incidents() -> tuple[IncidentScenario, ...]:
    """Build all 15 deterministic benchmark scenarios."""
    return tuple(build_benchmark_incident(f"INC-{number:03d}") for number in range(1, 16))
