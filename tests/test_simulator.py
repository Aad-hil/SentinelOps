from simulator.generator import (
    generate_incident_deployments,
    generate_incident_logs,
    generate_incident_metrics,
)
from simulator.incidents import INCIDENT_001


def test_incident_definition():
    assert INCIDENT_001.incident_id == "INC-001"
    assert INCIDENT_001.service == "checkout-service"
    assert INCIDENT_001.severity == "HIGH"


def test_incident_logs():
    logs = generate_incident_logs(INCIDENT_001.detected_at)

    assert len(logs) == 5
    assert any("connection pool exhausted" in log.message for log in logs)


def test_incident_metrics():
    metrics = generate_incident_metrics(INCIDENT_001.detected_at)

    assert len(metrics) == 8

    pool_metrics = [
        metric
        for metric in metrics
        if metric.metric_name == "db_pool_utilization_percent"
    ]

    assert max(metric.value for metric in pool_metrics) == 100


def test_incident_deployment():
    deployments = generate_incident_deployments(INCIDENT_001.detected_at)

    assert len(deployments) == 1
    assert deployments[0].version == "checkout-v42"
    assert deployments[0].previous_version == "checkout-v41"
    assert deployments[0].changes["DB_POOL_SIZE"] == "20"