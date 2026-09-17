from graph.state import AgentFinding, InvestigationState, append_finding
from tools.telemetry import query_logs, query_metrics, query_traces


def run_telemetry_agent(state: InvestigationState) -> dict:
    """Investigate telemetry through the dedicated telemetry tool layer."""
    evidence = state["evidence"]

    error_logs = query_logs(evidence, level="ERROR")
    error_traces = query_traces(evidence, status="ERROR")
    metrics = query_metrics(evidence, service=evidence.incident.service)

    metric_names = sorted({metric.metric_name for metric in metrics})
    evidence_refs = tuple(
        [
            f"error_logs={len(error_logs)}",
            f"error_traces={len(error_traces)}",
            f"metric_points={len(metrics)}",
        ]
        + metric_names
    )

    summary = (
        f"Telemetry tools found {len(error_logs)} error logs, "
        f"{len(error_traces)} error traces, and {len(metrics)} service metric points "
        f"for {evidence.incident.service}."
    )

    finding = AgentFinding(
        agent="telemetry",
        category="telemetry",
        summary=summary,
        evidence=evidence_refs,
        confidence=0.75 if error_logs or error_traces else 0.45,
    )
    return append_finding(state, finding)
