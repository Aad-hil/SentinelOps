from graph.state import AgentFinding, InvestigationState, append_finding
from tools.deployments import get_deployment_changes, get_recent_deployments


def run_deployment_agent(state: InvestigationState) -> dict:
    """Inspect deployment history through the agent's dedicated tools."""

    evidence = state["evidence"]
    recent = get_recent_deployments(evidence)

    if recent:
        deployment = recent[0]
        changes = get_deployment_changes(evidence, deployment.version)
        change_refs = tuple(
            f"change:{key}={value}" for key, value in sorted((changes.changes if changes else {}).items())
        )
        summary = (
            f"Latest deployment before detection was {deployment.version} for "
            f"{deployment.service}, following {deployment.previous_version}."
        )
        refs = (
            deployment.version,
            deployment.previous_version,
            deployment.timestamp.isoformat(),
            *change_refs,
        )
        confidence = 0.8
    else:
        summary = "No deployment was found before incident detection."
        refs = ()
        confidence = 0.55

    finding = AgentFinding(
        agent="deployment",
        category="deployment",
        summary=summary,
        evidence=refs,
        confidence=confidence,
    )
    return append_finding(state, finding)
