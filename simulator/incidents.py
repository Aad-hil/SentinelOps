from datetime import UTC, datetime

from simulator.models import Incident

INCIDENT_001 = Incident(
    incident_id="INC-001",
    service="checkout-service",
    severity="HIGH",
    title="Checkout latency spike",
    description=(
        "Checkout-service p95 latency increased significantly, "
        "causing elevated request failures."
    ),
    detected_at=datetime(
        2026,
        9,
        16,
        14,
        32,
        tzinfo=UTC,
    ),
)
