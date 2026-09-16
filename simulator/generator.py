from datetime import datetime, timedelta

from simulator.models import (
    DeploymentEvent,
    LogEvent,
    MetricPoint,
    TraceSpan,
)


def generate_incident_logs(start: datetime) -> list[LogEvent]:
    """Generate realistic application logs for INC-001."""

    return [
        LogEvent(
            timestamp=start - timedelta(minutes=5),
            service="checkout-service",
            level="INFO",
            message="checkout request completed successfully",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=4),
            service="payment-service",
            level="INFO",
            message="payment authorization completed successfully",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=3),
            service="inventory-service",
            level="INFO",
            message="inventory reservation completed successfully",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=2),
            service="checkout-service",
            level="INFO",
            message="deployment checkout-v42 completed successfully",
        ),
        LogEvent(
            timestamp=start,
            service="checkout-service",
            level="WARN",
            message="database connection acquisition exceeded 500ms",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=1),
            service="checkout-service",
            level="WARN",
            message="database connection wait time increasing",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=1),
            service="payment-service",
            level="INFO",
            message="payment authorization latency within normal range",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=1),
            service="inventory-service",
            level="INFO",
            message="inventory reservation latency within normal range",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=2),
            service="checkout-service",
            level="WARN",
            message="database connection acquisition exceeded 1000ms",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=3),
            service="checkout-service",
            level="ERROR",
            message="failed to acquire database connection",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=4),
            service="checkout-service",
            level="ERROR",
            message="database connection pool exhausted",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=4),
            service="order-db",
            level="WARN",
            message="connection request queue depth increasing",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=5),
            service="checkout-service",
            level="ERROR",
            message="checkout request failed",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=6),
            service="checkout-service",
            level="ERROR",
            message="checkout error rate exceeded alert threshold",
        ),
    ]


def generate_incident_metrics(start: datetime) -> list[MetricPoint]:
    """Generate correlated metrics for INC-001."""

    metrics: list[MetricPoint] = []

    latency_values = [320, 340, 380, 410, 900, 1800, 2800, 4100]
    for minute, value in enumerate(latency_values):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="http_request_duration_ms",
                service="checkout-service",
                value=value,
            )
        )

    pool_values = [61, 65, 72, 84, 94, 98, 100, 100]
    for minute, value in enumerate(pool_values):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="db_pool_utilization_percent",
                service="checkout-service",
                value=value,
            )
        )

    wait_values = [40, 50, 80, 150, 400, 700, 1200, 1500]
    for minute, value in enumerate(wait_values):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="db_connection_wait_ms",
                service="checkout-service",
                value=value,
            )
        )

    error_values = [0.2, 0.2, 0.3, 0.5, 1.2, 3.5, 7.8, 12.4]
    for minute, value in enumerate(error_values):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="checkout_error_rate_percent",
                service="checkout-service",
                value=value,
            )
        )

    payment_latency = [210, 215, 208, 220, 212, 218, 214, 216]
    for minute, value in enumerate(payment_latency):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="http_request_duration_ms",
                service="payment-service",
                value=value,
            )
        )

    inventory_latency = [180, 175, 182, 179, 181, 177, 180, 183]
    for minute, value in enumerate(inventory_latency):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="http_request_duration_ms",
                service="inventory-service",
                value=value,
            )
        )

    return metrics


def generate_incident_deployments(start: datetime) -> list[DeploymentEvent]:
    """Generate deployment history surrounding INC-001."""

    return [
        DeploymentEvent(
            timestamp=start - timedelta(minutes=7),
            service="payment-service",
            version="payment-v18",
            previous_version="payment-v17",
            changes={"PAYMENT_TIMEOUT_MS": "3000"},
        ),
        DeploymentEvent(
            timestamp=start - timedelta(minutes=2),
            service="checkout-service",
            version="checkout-v42",
            previous_version="checkout-v41",
            changes={"DB_POOL_SIZE": "20"},
        ),
        DeploymentEvent(
            timestamp=start - timedelta(minutes=1),
            service="inventory-service",
            version="inventory-v27",
            previous_version="inventory-v26",
            changes={"CACHE_TTL_SECONDS": "300"},
        ),
    ]


def generate_incident_traces(start: datetime) -> list[TraceSpan]:
    """Generate distributed trace spans for INC-001."""

    traces: list[TraceSpan] = []

    for minute in range(8):
        timestamp = start + timedelta(minutes=minute)

        checkout_duration = 320 + (minute * 500)
        traces.append(
            TraceSpan(
                timestamp=timestamp,
                trace_id=f"trace-{minute:03d}",
                service="checkout-service",
                operation="POST /checkout",
                duration_ms=checkout_duration,
                status="OK" if minute < 4 else "ERROR",
            )
        )

        db_duration = 80 + (minute * 300)
        traces.append(
            TraceSpan(
                timestamp=timestamp,
                trace_id=f"trace-{minute:03d}",
                service="order-db",
                operation="acquire_connection",
                duration_ms=db_duration,
                status="OK" if minute < 4 else "ERROR",
            )
        )

        traces.append(
            TraceSpan(
                timestamp=timestamp,
                trace_id=f"trace-{minute:03d}",
                service="payment-service",
                operation="POST /authorize",
                duration_ms=210,
                status="OK",
            )
        )

    return traces


def generate_incident_002_logs(start: datetime) -> list[LogEvent]:
    """Generate synthetic telemetry logs for the GitHub-derived scenario."""

    return [
        LogEvent(
            timestamp=start - timedelta(minutes=5),
            service="github-web",
            level="INFO",
            message="update request latency within baseline range",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=4),
            service="github-web",
            level="INFO",
            message="deployment web-2025.01.09.3 completed successfully",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=2),
            service="github-web",
            level="WARN",
            message="database query fingerprint q7f2 execution time above baseline",
        ),
        LogEvent(
            timestamp=start - timedelta(minutes=1),
            service="github-web",
            level="WARN",
            message="primary database queue depth increasing",
        ),
        LogEvent(
            timestamp=start,
            service="github-web",
            level="WARN",
            message="update request latency exceeded 500ms",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=1),
            service="github-web",
            level="ERROR",
            message="update request returned 5xx",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=2),
            service="github-web",
            level="ERROR",
            message="update request failure rate exceeded alert threshold",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=4),
            service="db-primary-01",
            level="WARN",
            message="database workload saturation detected",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=8),
            service="github-web",
            level="WARN",
            message="multiple update paths reporting elevated latency",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=12),
            service="github-web",
            level="INFO",
            message="investigation tooling identified query fingerprint q7f2 as high load",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=16),
            service="github-web",
            level="INFO",
            message="deployment web-2025.01.09.3 rollback initiated",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=30),
            service="github-web",
            level="INFO",
            message="update request error rate returned toward baseline",
        ),
    ]


def generate_incident_002_metrics(start: datetime) -> list[MetricPoint]:
    """Generate synthetic correlated metrics for the GitHub-derived scenario."""

    metrics: list[MetricPoint] = []
    series = {
        "db_primary_cpu_percent": [52, 57, 68, 79, 91, 96, 98, 99],
        "db_query_latency_ms": [42, 48, 71, 110, 260, 540, 880, 1120],
        "db_queue_depth": [8, 10, 15, 24, 41, 63, 78, 84],
        "update_request_latency_ms": [180, 185, 210, 260, 430, 680, 940, 1180],
        "update_request_error_rate_percent": [0.2, 0.3, 0.4, 0.8, 2.1, 4.7, 6.85, 6.1],
    }

    for metric_name, values in series.items():
        service = "db-primary-01" if metric_name.startswith("db_") else "github-web"
        for minute, value in enumerate(values):
            metrics.append(
                MetricPoint(
                    timestamp=start + timedelta(minutes=minute),
                    metric_name=metric_name,
                    service=service,
                    value=value,
                )
            )

    healthy_values = [205, 210, 208, 212, 207, 211, 209, 213]
    for minute, value in enumerate(healthy_values):
        metrics.append(
            MetricPoint(
                timestamp=start + timedelta(minutes=minute),
                metric_name="read_request_latency_ms",
                service="github-web",
                value=value,
            )
        )

    return metrics


def generate_incident_002_deployments(start: datetime) -> list[DeploymentEvent]:
    """Generate synthetic deployment history for the GitHub-derived scenario."""

    return [
        DeploymentEvent(
            timestamp=start - timedelta(minutes=4),
            service="github-web",
            version="web-2025.01.09.3",
            previous_version="web-2025.01.09.2",
            changes={
                "query_fingerprint": "q7f2",
                "query_path": "update_records",
            },
        ),
        DeploymentEvent(
            timestamp=start + timedelta(minutes=16),
            service="github-web",
            version="web-2025.01.09.2",
            previous_version="web-2025.01.09.3",
            changes={"action": "rollback"},
        ),
        DeploymentEvent(
            timestamp=start + timedelta(minutes=24),
            service="github-web",
            version="web-2025.01.09.2",
            previous_version="web-2025.01.09.2",
            changes={"status": "stable"},
        ),
    ]


def generate_incident_002_traces(start: datetime) -> list[TraceSpan]:
    """Generate synthetic distributed traces for the GitHub-derived scenario."""

    traces: list[TraceSpan] = []
    update_durations = [180, 190, 220, 280, 450, 720, 980, 1240]
    query_durations = [42, 48, 71, 110, 260, 540, 880, 1120]

    for minute, (update_duration, query_duration) in enumerate(
        zip(update_durations, query_durations, strict=True)
    ):
        timestamp = start + timedelta(minutes=minute)
        status = "OK" if minute < 4 else "ERROR"
        trace_id = f"github-trace-{minute:03d}"

        traces.append(
            TraceSpan(
                timestamp=timestamp,
                trace_id=trace_id,
                service="github-web",
                operation="PATCH /update",
                duration_ms=update_duration,
                status=status,
            )
        )
        traces.append(
            TraceSpan(
                timestamp=timestamp,
                trace_id=trace_id,
                service="db-primary-01",
                operation="execute q7f2",
                duration_ms=query_duration,
                status=status,
            )
        )
        traces.append(
            TraceSpan(
                timestamp=timestamp,
                trace_id=trace_id,
                service="github-web",
                operation="GET /status",
                duration_ms=120,
                status="OK",
            )
        )

    return traces
