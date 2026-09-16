from simulator.generator import (
    generate_incident_deployments,
    generate_incident_logs,
    generate_incident_metrics,
    generate_incident_traces,
)
from simulator.incidents import (
    INCIDENT_001,
    INCIDENT_001_GROUND_TRUTH,
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
