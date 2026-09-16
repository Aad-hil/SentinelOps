from datetime import datetime, timedelta

from simulator.models import DeploymentEvent, LogEvent, MetricPoint


def generate_incident_logs(start: datetime) -> list[LogEvent]:
    """Generate application logs for INC-001."""

    return [
        LogEvent(
            timestamp=start,
            service="checkout-service",
            level="INFO",
            message="checkout request processing started",
        ),
        LogEvent(
            timestamp=start + timedelta(minutes=2),
            service="checkout-service",
            level="WARN",
            message="database connection acquisition exceeded 500ms",
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
            timestamp=start + timedelta(minutes=5),
            service="checkout-service",
            level="ERROR",
            message="checkout request failed",
        ),
    ]


def generate_incident_metrics(start: datetime) -> list[MetricPoint]:
    """Generate application and database metrics for INC-001."""

    return [
        # Checkout latency
        MetricPoint(
            timestamp=start,
            metric_name="http_request_duration_ms",
            service="checkout-service",
            value=320,
        ),
        MetricPoint(
            timestamp=start + timedelta(minutes=1),
            metric_name="http_request_duration_ms",
            service="checkout-service",
            value=410,
        ),
        MetricPoint(
            timestamp=start + timedelta(minutes=2),
            metric_name="http_request_duration_ms",
            service="checkout-service",
            value=2800,
        ),
        MetricPoint(
            timestamp=start + timedelta(minutes=3),
            metric_name="http_request_duration_ms",
            service="checkout-service",
            value=4100,
        ),
        # Database connection pool utilization
        MetricPoint(
            timestamp=start,
            metric_name="db_pool_utilization_percent",
            service="checkout-service",
            value=61,
        ),
        MetricPoint(
            timestamp=start + timedelta(minutes=1),
            metric_name="db_pool_utilization_percent",
            service="checkout-service",
            value=72,
        ),
        MetricPoint(
            timestamp=start + timedelta(minutes=2),
            metric_name="db_pool_utilization_percent",
            service="checkout-service",
            value=98,
        ),
        MetricPoint(
            timestamp=start + timedelta(minutes=3),
            metric_name="db_pool_utilization_percent",
            service="checkout-service",
            value=100,
        ),
    ]


def generate_incident_deployments(
    start: datetime,
) -> list[DeploymentEvent]:
    """Generate deployment history for INC-001."""

    return [
        DeploymentEvent(
            timestamp=start - timedelta(minutes=7),
            service="checkout-service",
            version="checkout-v42",
            previous_version="checkout-v41",
            changes={
                "DB_POOL_SIZE": "20",
            },
        )
    ]