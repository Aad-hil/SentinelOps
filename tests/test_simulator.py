from simulator.generator import (
    generate_incident_deployments,
    generate_incident_logs,
    generate_incident_metrics,
    generate_incident_traces,
)
from simulator.incidents import INCIDENT_001
from simulator.scenarios import build_incident_001


def test_incident_definition():
    assert INCIDENT_001.incident_id == "INC-001"
    assert INCIDENT_001.service == "checkout-service"
    assert INCIDENT_001.severity == "HIGH"
    assert INCIDENT_001.started_at < INCIDENT_001.detected_at


def test_incident_logs():
    logs = generate_incident_logs(INCIDENT_001.detected_at)

    assert len(logs) == 14
    assert any("connection pool exhausted" in log.message for log in logs)


def test_incident_metrics():
    metrics = generate_incident_metrics(INCIDENT_001.detected_at)

    assert len(metrics) == 48

    pool_metrics = [
        metric
        for metric in metrics
        if metric.metric_name == "db_pool_utilization_percent"
    ]

    assert len(pool_metrics) == 8
    assert max(metric.value for metric in pool_metrics) == 100


def test_incident_deployments():
    deployments = generate_incident_deployments(INCIDENT_001.detected_at)

    assert len(deployments) == 3

    checkout_deployment = next(
        deployment
        for deployment in deployments
        if deployment.service == "checkout-service"
    )

    assert checkout_deployment.version == "checkout-v42"
    assert checkout_deployment.previous_version == "checkout-v41"
    assert checkout_deployment.changes["DB_POOL_SIZE"] == "20"


def test_incident_traces():
    traces = generate_incident_traces(INCIDENT_001.detected_at)

    assert len(traces) == 24

    database_spans = [
        trace
        for trace in traces
        if trace.service == "order-db"
    ]

    assert len(database_spans) == 8
    assert max(trace.duration_ms for trace in database_spans) == 2180


def test_incident_scenario():
    scenario = build_incident_001()

    assert scenario.incident.incident_id == "INC-001"
    assert len(scenario.logs) == 14
    assert len(scenario.metrics) == 48
    assert len(scenario.deployments) == 3
    assert len(scenario.traces) == 24
    assert "Database connection pool exhaustion" in scenario.ground_truth.root_cause
