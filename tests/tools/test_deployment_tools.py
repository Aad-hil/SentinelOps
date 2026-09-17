from simulator.scenarios import build_incident_002_evidence
from tools.deployments import get_deployment_changes, get_recent_deployments


def test_get_recent_deployments_returns_newest_first_before_detection():
    evidence = build_incident_002_evidence()

    deployments = get_recent_deployments(evidence)

    assert len(deployments) == 1
    assert deployments[0].version == "web-2025.01.09.3"
    assert deployments[0].previous_version == "web-2025.01.09.2"


def test_get_recent_deployments_can_include_post_detection_events():
    evidence = build_incident_002_evidence()

    deployments = get_recent_deployments(evidence, before_detection=False)

    assert len(deployments) == 3
    assert deployments[0].changes["status"] == "stable"


def test_get_deployment_changes_finds_version_metadata():
    evidence = build_incident_002_evidence()

    deployment = get_deployment_changes(evidence, "web-2025.01.09.3")

    assert deployment is not None
    assert deployment.changes["query_fingerprint"] == "q7f2"
    assert deployment.changes["query_path"] == "update_records"


def test_get_deployment_changes_returns_none_for_unknown_version():
    evidence = build_incident_002_evidence()

    assert get_deployment_changes(evidence, "unknown") is None
