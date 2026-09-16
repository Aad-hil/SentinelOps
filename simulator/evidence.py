from dataclasses import dataclass

from simulator.models import (
    DeploymentEvent,
    Incident,
    LogEvent,
    MetricPoint,
    TraceSpan,
)


@dataclass(frozen=True)
class EvidenceBundle:
    """Investigation evidence exposed to agents without ground truth."""

    incident: Incident
    logs: tuple[LogEvent, ...]
    metrics: tuple[MetricPoint, ...]
    deployments: tuple[DeploymentEvent, ...]
    traces: tuple[TraceSpan, ...]


def build_evidence_bundle(
    incident: Incident,
    logs: tuple[LogEvent, ...],
    metrics: tuple[MetricPoint, ...],
    deployments: tuple[DeploymentEvent, ...],
    traces: tuple[TraceSpan, ...],
) -> EvidenceBundle:
    """Build the agent-facing evidence bundle.

    Ground truth is intentionally not accepted by this function. This keeps
    evaluation data separate from the evidence available during investigation.
    """

    return EvidenceBundle(
        incident=incident,
        logs=logs,
        metrics=metrics,
        deployments=deployments,
        traces=traces,
    )
