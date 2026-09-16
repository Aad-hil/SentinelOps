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
