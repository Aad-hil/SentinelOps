from graph.state import AgentFinding, InvestigationState, append_finding


def run_deployment_agent(state: InvestigationState) -> dict:
    """Inspect deployment events independently from telemetry and knowledge."""

    deployments = state["evidence"].deployments
    incident_time = state["evidence"].incident.detected_at

    recent = [deployment for deployment in deployments if deployment.timestamp <= incident_time]
    recent.sort(key=lambda deployment: deployment.timestamp, reverse=True)

    if recent:
        deployment = recent[0]
        summary = (
            f"Latest deployment before detection was {deployment.version} for "
            f"{deployment.service}, following {deployment.previous_version}."
        )
        refs = (
            deployment.version,
            deployment.previous_version,
            deployment.timestamp.isoformat(),
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
