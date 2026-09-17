from datetime import datetime, timezone

from memory.models import IncidentMemory


def test_incident_memory_builds_deterministic_search_text():
    memory = IncidentMemory(
        incident_id="INC-002",
        service="github-web",
        severity="HIGH",
        title="Primary database saturation after deployment",
        description="Update requests experienced elevated errors.",
        root_cause_hypothesis_id="H1",
        root_cause_statement="A recent deployment introduced a database-impacting change that caused primary database saturation.",
        root_cause_confidence=0.95,
        resolution_summary="Problematic deployment was rolled back and service recovered.",
        recovery_action="Rollback deployment web-2025.01.09.3",
        created_at=datetime(2025, 1, 9, 1, 26, tzinfo=timezone.utc),
        completed_at=datetime(2025, 1, 9, 1, 56, tzinfo=timezone.utc),
    )

    text = memory.to_search_text()

    assert "Primary database saturation after deployment" in text
    assert "service: github-web" in text
    assert "root cause: A recent deployment" in text
    assert "resolution: Problematic deployment" in text
    assert "recovery action: Rollback deployment" in text


def test_incident_memory_allows_unknown_root_cause_fields():
    memory = IncidentMemory(
        incident_id="INC-TEST",
        service="checkout",
        severity="MEDIUM",
        title="Elevated latency",
        description="Requests became slow.",
        root_cause_hypothesis_id=None,
        root_cause_statement=None,
        root_cause_confidence=None,
        resolution_summary=None,
        recovery_action=None,
    )

    assert memory.to_search_text() == (
        "Elevated latency\n"
        "Requests became slow.\n"
        "service: checkout\n"
        "severity: MEDIUM"
    )
