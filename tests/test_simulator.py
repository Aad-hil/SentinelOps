from simulator.generator import (
    generate_incident_002_deployments,
    generate_incident_002_logs,
    generate_incident_002_metrics,
    generate_incident_002_traces,
    generate_incident_deployments,
    generate_incident_logs,
    generate_incident_metrics,
    generate_incident_traces,
)
from simulator.incidents import INCIDENT_001, INCIDENT_002
from simulator.scenarios import build_incident_001, build_incident_002


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


def test_incident_002_definition():
    assert INCIDENT_002.incident_id == "INC-002"
    assert INCIDENT_002.service == "github-web"
    assert INCIDENT_002.severity == "HIGH"
    assert INCIDENT_002.started_at < INCIDENT_002.detected_at


def test_incident_002_evidence():
    logs = generate_incident_002_logs(INCIDENT_002.detected_at)
    metrics = generate_incident_002_metrics(INCIDENT_002.detected_at)
    deployments = generate_incident_002_deployments(INCIDENT_002.detected_at)
    traces = generate_incident_002_traces(INCIDENT_002.detected_at)

    assert len(logs) == 12
    assert len(metrics) == 48
    assert len(deployments) == 3
    assert len(traces) == 24

    query_metrics = [
        metric for metric in metrics if metric.metric_name == "db_query_latency_ms"
    ]
    db_cpu = [
        metric for metric in metrics if metric.metric_name == "db_primary_cpu_percent"
    ]
    error_rates = [
        metric
        for metric in metrics
        if metric.metric_name == "update_request_error_rate_percent"
    ]

    assert query_metrics[0].value < query_metrics[-1].value
    assert db_cpu[0].value < db_cpu[-1].value
    assert max(metric.value for metric in error_rates) == 6.85

    rollback = next(
        deployment
        for deployment in deployments
        if deployment.changes.get("action") == "rollback"
    )
    assert rollback.timestamp > INCIDENT_002.detected_at


def test_incident_002_scenario():
    scenario = build_incident_002()

    assert scenario.incident.incident_id == "INC-002"
    assert len(scenario.logs) == 12
    assert len(scenario.metrics) == 48
    assert len(scenario.deployments) == 3
    assert len(scenario.traces) == 24
    assert "deployment" in scenario.ground_truth.trigger.lower()
