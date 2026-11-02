from datetime import datetime, timezone

from memory.builders import build_incident_memory
from recovery.models import RecoveryPlan, RecoveryStep
from simulator.scenarios import build_incident_002_evidence


def test_build_incident_memory_uses_adjudicated_hypothesis_and_actual_plan():
    evidence = build_incident_002_evidence()
    state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
        "hypotheses": [],
        "adjudication": None,
        "recovery_plan": RecoveryPlan(
            incident_id="INC-002",
            hypothesis_id="H1",
            confidence=0.95,
            readiness="ready_for_review",
            rationale="The plan is supported by the incident evidence.",
            steps=(
                RecoveryStep(
                    step_id="inspect-query",
                    action="Inspect the query associated with the deployment.",
                    purpose="Validate the suspected trigger.",
                    risk="low",
                    requires_approval=False,
                    evidence=("deployment:web-2025.01.09.3",),
                ),
                RecoveryStep(
                    step_id="rollback",
                    action="Roll back the problematic deployment after approval.",
                    purpose="Remove the suspected trigger.",
                    risk="medium",
                    requires_approval=True,
                    evidence=("deployment:web-2025.01.09.3",),
                ),
            ),
        ),
    }

    from agents.root_cause import generate_hypotheses
    from agents.adjudication import adjudicate_hypotheses
    from graph.evidence import EvidenceItem

    state["evidence_items"] = [
        EvidenceItem(
            source="deployment:web-2025.01.09.3",
            evidence_type="deployment",
            observation="deployment query_fingerprint=q7f2 query_path=update_records",
            timestamp=datetime(2025, 1, 9, 1, 22, tzinfo=timezone.utc),
            relevance=1.0,
            agent="deployment",
        ),
        EvidenceItem(
            source="log:2025-01-09T01:42:00+00:00",
            evidence_type="log",
            observation="primary database saturation caused elevated update error rate",
            timestamp=datetime(2025, 1, 9, 1, 42, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
        EvidenceItem(
            source="rollback",
            evidence_type="recovery",
            observation="rollback completed and error rate returned toward baseline",
            timestamp=datetime(2025, 1, 9, 1, 56, tzinfo=timezone.utc),
            relevance=1.0,
            agent="telemetry",
        ),
    ]
    state["hypotheses"] = generate_hypotheses(state)
    state["hypotheses"], state["adjudication"] = adjudicate_hypotheses(state)

    memory = build_incident_memory(state)

    assert memory.incident_id == "INC-002"
    assert memory.service == "github-web"
    assert memory.root_cause_hypothesis_id == "H1"
    assert memory.root_cause_statement is not None
    assert memory.root_cause_confidence is not None
    assert memory.resolution_summary is None
    assert memory.recovery_action == (
        "Inspect the query associated with the deployment.; "
        "Roll back the problematic deployment after approval."
    )
    assert memory.created_at == evidence.incident.detected_at
    assert memory.completed_at is not None


def test_build_incident_memory_handles_missing_adjudication_and_plan():
    evidence = build_incident_002_evidence()
    state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }

    memory = build_incident_memory(state)

    assert memory.incident_id == "INC-002"
    assert memory.root_cause_hypothesis_id is None
    assert memory.root_cause_statement is None
    assert memory.root_cause_confidence is None
    assert memory.resolution_summary is None
    assert memory.recovery_action is None
