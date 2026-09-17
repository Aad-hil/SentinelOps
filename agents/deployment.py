from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_agent_evidence, append_finding
from tools.deployments import get_deployment_changes, get_recent_deployments


def run_deployment_agent(state: InvestigationState) -> dict:
    """Investigate deployment history and publish normalized evidence."""
    evidence = state["evidence"]
    recent = get_recent_deployments(evidence)

    items: list[EvidenceItem] = []
    if recent:
        deployment = recent[0]
        changes = get_deployment_changes(evidence, deployment.version)
        change_refs = tuple(
            f"change:{key}={value}"
            for key, value in sorted((changes.changes if changes else {}).items())
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
        items.append(EvidenceItem(
            source=f"deployment:{deployment.version}",
            evidence_type="deployment",
            observation=(
                f"{deployment.service} changed from {deployment.previous_version} "
                f"to {deployment.version}"
            ),
            timestamp=deployment.timestamp,
            relevance=0.9,
            agent="deployment",
        ))
        for key, value in sorted(deployment.changes.items()):
            items.append(EvidenceItem(
                source=f"deployment:{deployment.version}:{key}",
                evidence_type="deployment_change",
                observation=f"{key}={value}",
                timestamp=deployment.timestamp,
                relevance=0.85,
                agent="deployment",
            ))
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
    result = append_finding(state, finding)
    result.update(append_agent_evidence(state, items))
    return result
