from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_agent_evidence, append_finding
from tools.telemetry import query_logs, query_metrics, query_traces


def run_telemetry_agent(state: InvestigationState) -> dict:
    """Investigate telemetry and publish normalized evidence."""
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

    items: list[EvidenceItem] = []
    for log in error_logs:
        items.append(EvidenceItem(
            source=f"log:{log.timestamp.isoformat()}",
            evidence_type="log",
            observation=log.message,
            timestamp=log.timestamp,
            relevance=0.8,
            agent="telemetry",
        ))
    for trace in error_traces:
        items.append(EvidenceItem(
            source=f"trace:{trace.trace_id}",
            evidence_type="trace",
            observation=(
                f"{trace.operation} returned ERROR with duration {trace.duration_ms:.1f}ms"
            ),
            timestamp=trace.timestamp,
            relevance=0.75,
            agent="telemetry",
        ))
    for metric in metrics:
        items.append(EvidenceItem(
            source=f"metric:{metric.metric_name}:{metric.timestamp.isoformat()}",
            evidence_type="metric",
            observation=f"{metric.metric_name}={metric.value}",
            timestamp=metric.timestamp,
            relevance=0.7,
            agent="telemetry",
        ))

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
    result = append_finding(state, finding)
    result.update(append_agent_evidence(state, items))
    return result
