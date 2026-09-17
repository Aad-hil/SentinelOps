from simulator.evidence import EvidenceBundle
from simulator.models import DeploymentEvent


def get_recent_deployments(
    evidence: EvidenceBundle,
    *,
    service: str | None = None,
    before_detection: bool = True,
) -> list[DeploymentEvent]:
    """Return deployment events ordered newest-first."""
    incident_time = evidence.incident.detected_at
    deployments = list(evidence.deployments)

    if service is not None:
        deployments = [deployment for deployment in deployments if deployment.service == service]
    if before_detection:
        deployments = [deployment for deployment in deployments if deployment.timestamp <= incident_time]

    return sorted(deployments, key=lambda deployment: deployment.timestamp, reverse=True)


def get_deployment_changes(
    evidence: EvidenceBundle,
    version: str,
) -> DeploymentEvent | None:
    """Return metadata for a specific deployment version."""
    for deployment in evidence.deployments:
        if deployment.version == version:
            return deployment
    return None
