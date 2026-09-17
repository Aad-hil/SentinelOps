from graph.state import AgentFinding, InvestigationState, append_finding


def run_telemetry_agent(state: InvestigationState) -> dict:
    """Inspect logs, metrics, and traces and produce an independent finding."""

    evidence = state["evidence"]
    error_logs = [log for log in evidence.logs if log.level == "ERROR"]
    metric_names = {metric.metric_name for metric in evidence.metrics}
    error_traces = [trace for trace in evidence.traces if trace.status == "ERROR"]

    evidence_refs = tuple(
        [f"error_logs={len(error_logs)}", f"error_traces={len(error_traces)}"]
        + sorted(metric_names)
    )

    summary = (
        f"Observed {len(error_logs)} error logs, {len(error_traces)} error traces, "
        f"and {len(evidence.metrics)} metric points for {evidence.incident.service}."
    )

    finding = AgentFinding(
        agent="telemetry",
        category="telemetry",
        summary=summary,
        evidence=evidence_refs,
        confidence=0.75 if error_logs or error_traces else 0.45,
    )
    return append_finding(state, finding)
