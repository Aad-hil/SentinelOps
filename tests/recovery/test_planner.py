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
        "identify-query",
        "rollback-deployment",
        "verify-database-recovery",
    ]
    assert plan.steps[0].requires_approval is True
    assert plan.steps[1].requires_approval is False


def test_plan_is_blocked_without_adjudication():
    plan = build_recovery_plan(make_state())

    assert plan.readiness == "blocked"
    assert plan.hypothesis_id is None
    assert plan.steps[0].step_id == "verify-root-cause"
    assert plan.requires_approval is False


def test_plan_uses_hypothesis_specific_recovery_actions():
    adjudication = SimpleNamespace(
        hypothesis_id="H9",
        confidence=0.95,
        temporal_support=True,
        causal_support=True,
        recovery_support=True,
        alternative_gaps=(),
    )

    plan = build_recovery_plan(make_state(adjudication=adjudication))
    actions = [step.action.lower() for step in plan.steps]

    assert plan.readiness == "ready_for_review"
    assert any("expensive database" in action or "write/query" in action for action in actions)
    assert any("write latency" in action for action in actions)
    assert all(step.evidence == () for step in plan.steps)


def test_plan_supports_all_generic_hypothesis_templates():
    for hypothesis_id in [f"H{i}" for i in range(1, 13)]:
        adjudication = SimpleNamespace(
            hypothesis_id=hypothesis_id,
            confidence=0.95,
            temporal_support=True,
            causal_support=True,
            recovery_support=True,
            alternative_gaps=(),
        )
        plan = build_recovery_plan(make_state(adjudication=adjudication))
        assert plan.steps
        assert plan.readiness == "ready_for_review"
