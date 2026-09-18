from types import SimpleNamespace

from agents.recovery import run_recovery_agent


def test_recovery_agent_publishes_conservative_plan_when_evidence_is_incomplete():
    state = {
        "incident_id": "INC-001",
        "adjudication": SimpleNamespace(
            hypothesis_id="H1",
            confidence=0.55,
            temporal_support=False,
            causal_support=False,
            recovery_support=False,
            alternative_gaps=("post-rollback recovery evidence",),
        ),
        "critique": SimpleNamespace(
            missing_evidence=("deployment-to-query evidence",),
        ),
    }

    result = run_recovery_agent(state)

    assert result["recovery_plan"].readiness == "verification_required"
    assert result["findings"][0].category == "recovery_planning"
    assert result["completed_tasks"] == ["recovery"]
    assert "Recovery Agent created" in result["messages"][-1]


def test_recovery_agent_publishes_reviewable_plan_when_support_is_complete():
    state = {
        "incident_id": "INC-002",
        "adjudication": SimpleNamespace(
            hypothesis_id="H1",
            confidence=0.95,
            temporal_support=True,
            causal_support=True,
            recovery_support=True,
            alternative_gaps=(),
        ),
    }

    result = run_recovery_agent(state)

    plan = result["recovery_plan"]
    assert plan.readiness == "ready_for_review"
    assert plan.requires_approval is True
    assert result["findings"][0].confidence == 0.95
