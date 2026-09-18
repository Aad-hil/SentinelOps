from types import SimpleNamespace

from recovery.planner import build_recovery_plan


def make_state(**overrides):
    state = {"incident_id": "INC-001"}
    state.update(overrides)
    return state


def test_plan_requires_verification_when_causal_evidence_is_incomplete():
    adjudication = SimpleNamespace(
        hypothesis_id="H1",
        confidence=0.55,
        temporal_support=False,
        causal_support=False,
        recovery_support=False,
        alternative_gaps=("post-rollback recovery evidence",),
    )
    critique = SimpleNamespace(
        missing_evidence=("evidence linking the deployment to a specific database query",),
    )

    plan = build_recovery_plan(make_state(adjudication=adjudication, critique=critique))

    assert plan.readiness == "verification_required"
    assert plan.confidence == 0.55
    assert plan.requires_approval is True
    assert plan.steps[0].step_id == "collect-missing-evidence"
    assert any("database query" in evidence for evidence in plan.steps[0].evidence)


def test_plan_is_ready_for_review_only_after_all_support_checks():
    adjudication = SimpleNamespace(
        hypothesis_id="H1",
        confidence=0.95,
        temporal_support=True,
        causal_support=True,
        recovery_support=True,
        alternative_gaps=(),
    )

    plan = build_recovery_plan(make_state(adjudication=adjudication))

    assert plan.readiness == "ready_for_review"
    assert [step.step_id for step in plan.steps] == [
        "mitigate",
        "verify-recovery",
        "permanent-fix",
    ]
    assert plan.steps[0].requires_approval is True
    assert plan.steps[1].requires_approval is False


def test_plan_is_blocked_without_adjudication():
    plan = build_recovery_plan(make_state())

    assert plan.readiness == "blocked"
    assert plan.hypothesis_id is None
    assert plan.steps[0].step_id == "verify-root-cause"
    assert plan.requires_approval is False
