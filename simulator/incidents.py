from datetime import UTC, datetime

from simulator.models import GroundTruth, Incident


INCIDENT_001 = Incident(
    incident_id="INC-001",
    service="checkout-service",
    severity="HIGH",
    title="Checkout latency spike",
    description=(
        "Checkout-service p95 latency increased significantly, "
        "causing elevated request failures."
    ),
    started_at=datetime(2026, 9, 16, 14, 27, tzinfo=UTC),
    detected_at=datetime(2026, 9, 16, 14, 32, tzinfo=UTC),
)


INCIDENT_001_GROUND_TRUTH = GroundTruth(
    root_cause="Database connection pool exhaustion.",
    trigger="Checkout deployment checkout-v42.",
    affected_component="Order database connection pool.",
    mitigation="Increase connection pool capacity or roll back the deployment.",
    contributing_factors=(
        "The deployment changed DB_POOL_SIZE from 50 to 20.",
        "Database connection wait time increased.",
        "Connection pool utilization reached 100 percent.",
    ),
)


INCIDENT_002 = Incident(
    incident_id="INC-002",
    service="github-web",
    severity="HIGH",
    title="Primary database saturation after deployment",
    description=(
        "A production deployment introduced a problematic database query, "
        "causing saturation of a primary database server and elevated "
        "update-request errors."
    ),
    started_at=datetime(2025, 1, 9, 1, 12, tzinfo=UTC),
    detected_at=datetime(2025, 1, 9, 1, 26, tzinfo=UTC),
)


INCIDENT_002_GROUND_TRUTH = GroundTruth(
    root_cause=(
        "A deployment introduced a database query that saturated "
        "a primary database server."
    ),
    trigger="Production deployment introducing the problematic query.",
    affected_component="Primary database server.",
    mitigation="Identify the problematic query and roll back the deployment.",
    contributing_factors=(
        "The query created excessive load on the primary database.",
        "Database saturation caused elevated request failures.",
        "The problematic query was identified using internal tooling "
        "and dashboards.",
    ),
)
