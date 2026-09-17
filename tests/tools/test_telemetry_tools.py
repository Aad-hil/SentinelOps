from simulator.scenarios import build_incident_002_evidence
from tools.telemetry import query_logs, query_metrics, query_traces


def test_query_logs_filters_by_level():
    evidence = build_incident_002_evidence()

    errors = query_logs(evidence, level="ERROR")

    assert errors
    assert all(log.level == "ERROR" for log in errors)


def test_query_metrics_filters_by_metric_and_service():
    evidence = build_incident_002_evidence()

    metrics = query_metrics(
        evidence,
        metric_name="db_primary_cpu_percent",
        service="db-primary-01",
    )

    assert len(metrics) == 8
    assert all(metric.value >= 0 for metric in metrics)


def test_query_traces_filters_by_status():
    evidence = build_incident_002_evidence()

    traces = query_traces(evidence, status="ERROR")

    assert traces
    assert all(trace.status == "ERROR" for trace in traces)
