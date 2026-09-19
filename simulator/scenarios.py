from simulator.benchmark import build_all_benchmark_incidents, build_benchmark_incident
from simulator.evidence import EvidenceBundle, build_evidence_bundle
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
from simulator.incidents import (
    INCIDENT_001,
    INCIDENT_001_GROUND_TRUTH,
    INCIDENT_002,
    INCIDENT_002_GROUND_TRUTH,
)
from simulator.models import IncidentScenario


def build_incident_001() -> IncidentScenario:
    """Build the controlled synthetic baseline scenario."""
    incident = INCIDENT_001
    return IncidentScenario(
        incident=incident,
        logs=tuple(generate_incident_logs(incident.detected_at)),
        metrics=tuple(generate_incident_metrics(incident.detected_at)),
        deployments=tuple(generate_incident_deployments(incident.detected_at)),
        traces=tuple(generate_incident_traces(incident.detected_at)),
        ground_truth=INCIDENT_001_GROUND_TRUTH,
    )


def build_incident_002() -> IncidentScenario:
    """Build the synthetic reconstruction of the GitHub January 2025 incident."""
    incident = INCIDENT_002
    return IncidentScenario(
        incident=incident,
        logs=tuple(generate_incident_002_logs(incident.detected_at)),
        metrics=tuple(generate_incident_002_metrics(incident.detected_at)),
        deployments=tuple(generate_incident_002_deployments(incident.detected_at)),
        traces=tuple(generate_incident_002_traces(incident.detected_at)),
        ground_truth=INCIDENT_002_GROUND_TRUTH,
    )


def build_incident_001_evidence() -> EvidenceBundle:
    scenario = build_incident_001()
    return build_evidence_bundle(
        incident=scenario.incident,
        logs=scenario.logs,
        metrics=scenario.metrics,
        deployments=scenario.deployments,
        traces=scenario.traces,
    )


def build_incident_002_evidence() -> EvidenceBundle:
    scenario = build_incident_002()
    return build_evidence_bundle(
        incident=scenario.incident,
        logs=scenario.logs,
        metrics=scenario.metrics,
        deployments=scenario.deployments,
        traces=scenario.traces,
    )


def build_benchmark_evidence(incident_id: str) -> EvidenceBundle:
    """Build agent-facing evidence for any benchmark incident."""
    scenario = build_benchmark_incident(incident_id)
    return build_evidence_bundle(
        incident=scenario.incident,
        logs=scenario.logs,
        metrics=scenario.metrics,
        deployments=scenario.deployments,
        traces=scenario.traces,
    )
