from simulator.evidence import EvidenceBundle
from simulator.models import LogEvent, MetricPoint, TraceSpan


def query_logs(evidence: EvidenceBundle, *, level: str | None = None) -> list[LogEvent]:
    """Return incident logs, optionally filtered by log level."""
    logs = list(evidence.logs)
    if level is not None:
        normalized = level.upper()
        logs = [log for log in logs if log.level.upper() == normalized]
    return logs


def query_metrics(
    evidence: EvidenceBundle,
    *,
    metric_name: str | None = None,
    service: str | None = None,
) -> list[MetricPoint]:
    """Return incident metrics filtered by metric name and/or service."""
    metrics = list(evidence.metrics)
    if metric_name is not None:
        metrics = [metric for metric in metrics if metric.metric_name == metric_name]
    if service is not None:
        metrics = [metric for metric in metrics if metric.service == service]
    return metrics


def query_traces(
    evidence: EvidenceBundle,
    *,
    service: str | None = None,
    status: str | None = None,
) -> list[TraceSpan]:
    """Return incident traces filtered by service and/or status."""
    traces = list(evidence.traces)
    if service is not None:
        traces = [trace for trace in traces if trace.service == service]
    if status is not None:
        normalized = status.upper()
        traces = [trace for trace in traces if trace.status.upper() == normalized]
    return traces
