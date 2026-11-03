"""Deterministic synthetic Amazon Redshift incident scenarios.

All telemetry and AWS events generated here are simulated. No live AWS account,
cluster, CloudWatch namespace, or Redshift system table is queried.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from simulator.models import (
    DeploymentEvent,
    GroundTruth,
    Incident,
    IncidentScenario,
    LogEvent,
    MetricPoint,
    TraceSpan,
)


_REDSHIFT_CASES = (
    {
        "id": "RS-001",
        "category": "wlm_queue_contention",
        "title": "Redshift WLM queue saturation",
        "description": "A burst of concurrent analytical queries saturated a Redshift workload queue.",
        "trigger": {"workload_change": "concurrent dashboard refresh", "queue": "analytics"},
        "metrics": {
            "redshift_wlm_queue_wait_seconds": (0.2, 0.4, 1.8, 4.5, 12.0, 22.0, 26.0, 8.0),
            "redshift_queries_queued": (0, 1, 4, 9, 18, 27, 31, 7),
            "redshift_query_duration_seconds": (2, 3, 4, 8, 18, 32, 38, 11),
        },
        "operation": "execute analytical query",
        "cause": "Concurrent analytical workloads saturated the Redshift WLM queue.",
        "mitigation": "Review WLM queue configuration, workload priorities, and query concurrency.",
        "hypothesis": "RSH1",
    },
    {
        "id": "RS-002",
        "category": "sql_query_regression",
        "title": "Redshift SQL query-plan regression",
        "description": "A changed analytical query increased scan volume and execution time on Redshift.",
        "trigger": {"query_change": "reporting query revision", "query_id": "q-8821"},
        "metrics": {
            "redshift_query_runtime_seconds": (3, 4, 5, 12, 29, 48, 55, 14),
            "redshift_scan_bytes_gb": (2, 2, 3, 8, 18, 31, 36, 9),
            "redshift_cpu_utilization_percent": (42, 45, 51, 64, 78, 91, 94, 63),
        },
        "operation": "execute reporting query",
        "cause": "A query revision increased scan volume and degraded the execution plan.",
        "mitigation": "Compare query plans and query history, then correct or revert the SQL change.",
        "hypothesis": "RSH2",
    },
    {
        "id": "RS-003",
        "category": "compute_capacity_pressure",
        "title": "Redshift compute capacity pressure",
        "description": "A sustained increase in warehouse workload exceeded available Redshift compute headroom.",
        "trigger": {"workload_change": "sustained analytics workload growth"},
        "metrics": {
            "redshift_cpu_utilization_percent": (48, 55, 67, 78, 88, 95, 97, 91),
            "redshift_query_runtime_seconds": (3, 4, 5, 8, 14, 25, 31, 24),
            "redshift_queries_queued": (0, 0, 1, 2, 6, 11, 14, 10),
        },
        "operation": "run warehouse workload",
        "cause": "Sustained workload growth exceeded available Redshift compute capacity.",
        "mitigation": "Review workload demand and evaluate a controlled capacity or concurrency change.",
        "hypothesis": "RSH3",
    },
    {
        "id": "RS-004",
        "category": "copy_load_failure",
        "title": "Redshift COPY load failure",
        "description": "A scheduled COPY operation failed while loading data from S3 into Redshift.",
        "trigger": {"load_job": "nightly customer ingest", "operation": "COPY"},
        "metrics": {
            "redshift_copy_failed_files": (0, 0, 1, 4, 8, 8, 8, 0),
            "redshift_load_duration_seconds": (20, 22, 30, 65, 110, 130, 125, 24),
            "redshift_load_rows_per_second": (9000, 8800, 7200, 3100, 900, 300, 250, 8500),
        },
        "operation": "COPY data from S3",
        "cause": "The Redshift COPY workload encountered source-file or load-configuration failures.",
        "mitigation": "Inspect COPY error details, S3 objects, manifest, file format, and IAM role access.",
        "hypothesis": "RSH4",
    },
    {
        "id": "RS-005",
        "category": "spectrum_external_data",
        "title": "Redshift Spectrum external data failure",
        "description": "Spectrum queries failed while resolving external data and catalog metadata.",
        "trigger": {"dependency": "Glue Data Catalog", "operation": "Spectrum query"},
        "metrics": {
            "redshift_spectrum_scan_bytes_gb": (1, 2, 3, 3, 1, 0, 0, 0),
            "redshift_query_errors": (0, 0, 1, 5, 12, 15, 14, 1),
            "redshift_query_runtime_seconds": (4, 5, 7, 18, 32, 40, 38, 6),
        },
        "operation": "query external schema",
        "cause": "Spectrum external-data access or catalog metadata resolution failed.",
        "mitigation": "Validate external schema, Glue catalog metadata, S3 objects, and role permissions.",
        "hypothesis": "RSH5",
    },
    {
        "id": "RS-006",
        "category": "table_design_statistics",
        "title": "Redshift table skew and stale statistics",
        "description": "Uneven table distribution and stale statistics increased query work and execution time.",
        "trigger": {"maintenance_state": "statistics stale", "table": "fact_events"},
        "metrics": {
            "redshift_query_runtime_seconds": (4, 5, 8, 15, 28, 44, 49, 30),
            "redshift_cpu_utilization_percent": (45, 50, 61, 72, 83, 90, 92, 80),
            "redshift_scan_bytes_gb": (3, 4, 7, 13, 24, 33, 35, 22),
        },
        "operation": "scan fact_events",
        "cause": "Table distribution skew and stale statistics increased scan and query costs.",
        "mitigation": "Inspect table distribution, sort design, statistics freshness, and maintenance history.",
        "hypothesis": "RSH6",
    },
    {
        "id": "RS-007",
        "category": "query_spill_storage_pressure",
        "title": "Redshift query spill pressure",
        "description": "Large intermediate query results spilled to disk and increased execution latency.",
        "trigger": {"query_pattern": "large intermediate join"},
        "metrics": {
            "redshift_query_spill_gb": (0, 0, 2, 8, 19, 31, 35, 6),
            "redshift_query_runtime_seconds": (3, 4, 8, 16, 31, 52, 58, 18),
            "redshift_cpu_utilization_percent": (50, 55, 62, 74, 86, 93, 95, 70),
        },
        "operation": "execute large join",
        "cause": "A memory-intensive query spilled intermediate results to disk.",
        "mitigation": "Inspect query plan and spill details, then reduce intermediate data or adjust workload allocation.",
        "hypothesis": "RSH7",
    },
    {
        "id": "RS-008",
        "category": "iam_kms_authorization",
        "title": "Redshift S3 authorization failure",
        "description": "A Redshift data load failed after its associated role lost access to encrypted S3 objects.",
        "trigger": {"authorization_change": "role policy update", "dependency": "S3 and KMS"},
        "metrics": {
            "redshift_copy_errors": (0, 0, 2, 7, 11, 12, 10, 0),
            "redshift_load_rows_per_second": (8500, 8400, 3000, 0, 0, 0, 0, 8200),
            "redshift_load_duration_seconds": (20, 22, 50, 90, 120, 125, 110, 24),
        },
        "operation": "COPY encrypted S3 data",
        "cause": "The Redshift-associated IAM role lacked required S3 or KMS permissions.",
        "mitigation": "Review role association, trust policy, S3 permissions, and KMS key policy.",
        "hypothesis": "RSH8",
    },
    {
        "id": "RS-009",
        "category": "vpc_connectivity",
        "title": "Redshift client connectivity degradation",
        "description": "Client connection failures and timeouts disrupted access to the Redshift endpoint.",
        "trigger": {"network_change": "security group rule update"},
        "metrics": {
            "redshift_connection_failures": (0, 0, 1, 5, 13, 19, 20, 2),
            "redshift_connection_latency_ms": (20, 22, 25, 90, 240, 510, 620, 40),
            "redshift_query_errors": (0, 0, 0, 2, 8, 14, 15, 1),
        },
        "operation": "connect to Redshift endpoint",
        "cause": "A network-path or security-group change disrupted client connectivity to Redshift.",
        "mitigation": "Validate routing, security groups, DNS, endpoints, and client connectivity.",
        "hypothesis": "RSH9",
    },
    {
        "id": "RS-010",
        "category": "cluster_maintenance_health",
        "title": "Redshift cluster maintenance disruption",
        "description": "Cluster maintenance and node health events coincided with query failures and degraded service.",
        "trigger": {"cluster_event": "maintenance and node replacement"},
        "metrics": {
            "redshift_query_errors": (0, 0, 1, 7, 16, 18, 12, 2),
            "redshift_query_runtime_seconds": (3, 4, 8, 20, 35, 40, 25, 7),
            "redshift_cpu_utilization_percent": (40, 45, 52, 58, 62, 55, 48, 43),
        },
        "operation": "execute warehouse query",
        "cause": "A Redshift cluster maintenance or node-health event disrupted query service.",
        "mitigation": "Inspect cluster events and status, confirm AWS service health, and follow the recovery procedure.",
        "hypothesis": "RSH10",
    },
    {
        "id": "RS-011",
        "category": "data_sharing_consumer",
        "title": "Redshift data sharing consumer failure",
        "description": "A consumer warehouse could not query a shared dataset after a producer-side share change.",
        "trigger": {"data_share_change": "consumer authorization updated"},
        "metrics": {
            "redshift_query_errors": (0, 0, 1, 6, 12, 13, 11, 1),
            "redshift_query_runtime_seconds": (3, 4, 8, 18, 29, 32, 26, 5),
            "redshift_connection_failures": (0, 0, 0, 0, 1, 1, 0, 0),
        },
        "operation": "query shared dataset",
        "cause": "A producer or consumer data-share authorization/state change blocked access to shared data.",
        "mitigation": "Validate data-share state, producer and consumer authorization, and consumer query context.",
        "hypothesis": "RSH11",
    },
    {
        "id": "RS-012",
        "category": "unknown_compound",
        "title": "Unclassified Redshift workload degradation",
        "description": "Redshift query latency and errors increased, but the available signals do not yet distinguish a single cause.",
        "trigger": {"observation": "no confirmed initiating change"},
        "metrics": {
            "redshift_query_errors": (0, 0, 1, 3, 7, 9, 8, 5),
            "redshift_query_runtime_seconds": (4, 5, 8, 13, 19, 24, 22, 17),
            "redshift_cpu_utilization_percent": (50, 54, 60, 66, 72, 76, 74, 71),
        },
        "operation": "execute warehouse query",
        "cause": "Insufficient evidence to distinguish a specific Redshift workload failure.",
        "mitigation": "Collect query history, WLM state, cluster events, and dependency diagnostics before selecting a recovery action.",
        "hypothesis": "RSH12",
    },
)


def redshift_case_ids() -> tuple[str, ...]:
    return tuple(case["id"] for case in _REDSHIFT_CASES)


def build_redshift_incident(incident_id: str) -> IncidentScenario:
    """Build one synthetic Redshift incident without exposing its answer key."""
    case = next((item for item in _REDSHIFT_CASES if item["id"] == incident_id), None)
    if case is None:
        raise KeyError(f"Unknown Redshift incident: {incident_id}")

    index = int(incident_id.split("-")[1])
    started = datetime(2026, 10, 1, 12, 0, tzinfo=UTC) + timedelta(days=index)
    service = "amazon-redshift"
    incident = Incident(
        incident_id=incident_id,
        service=service,
        severity="HIGH",
        title=case["title"],
        description=case["description"],
        started_at=started,
        detected_at=started + timedelta(minutes=4),
    )
    deployment = DeploymentEvent(
        timestamp=started - timedelta(minutes=3),
        service=service,
        version=f"redshift-config-{index:02d}",
        previous_version=f"redshift-config-{index:02d}-previous",
        changes=case["trigger"],
    )
    logs = (
        LogEvent(started - timedelta(minutes=3), service, "INFO", f"Redshift change observed: {case['trigger']}"),
        LogEvent(started, service, "WARN", f"{case['category']} signal increased during {case['operation']}"),
        LogEvent(started + timedelta(minutes=3), service, "ERROR", f"Redshift query or workload impact observed: {case['operation']}"),
        LogEvent(started + timedelta(minutes=8), service, "INFO", "Synthetic observation window ended; no remediation was executed"),
    )
    metrics = tuple(
        MetricPoint(
            timestamp=started + timedelta(minutes=minute * 2),
            metric_name=metric_name,
            service=service,
            value=float(value),
        )
        for metric_name, values in case["metrics"].items()
        for minute, value in enumerate(values)
    )
    traces = tuple(
        TraceSpan(
            timestamp=started + timedelta(minutes=minute * 2),
            trace_id=f"{incident_id.lower()}-trace-{minute:03d}",
            service=service,
            operation=case["operation"],
            duration_ms=150.0 + minute * 190.0,
            status="OK" if minute < 3 else "ERROR",
        )
        for minute in range(8)
    )
    truth = GroundTruth(
        root_cause=case["cause"],
        trigger=str(case["trigger"]),
        affected_component="Amazon Redshift workload or its directly integrated AWS dependency",
        mitigation=case["mitigation"],
        contributing_factors=(case["category"],),
    )
    return IncidentScenario(
        incident=incident,
        logs=logs,
        metrics=metrics,
        deployments=(deployment,),
        traces=traces,
        ground_truth=truth,
    )


def build_all_redshift_incidents() -> tuple[IncidentScenario, ...]:
    return tuple(build_redshift_incident(case_id) for case_id in redshift_case_ids())
