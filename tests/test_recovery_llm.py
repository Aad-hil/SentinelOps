"""LLM recovery advice must never change the deterministic safety plan."""
from types import SimpleNamespace

from agents.recovery import run_recovery_agent
from recovery.models import RecoveryPlan, RecoveryStep
from safety.policy import evaluate_recovery_safety


def _plan():
    return RecoveryPlan(
        incident_id="RS-001", hypothesis_id="RSH1", confidence=0.7,
        readiness="verification_required", rationale="Missing evidence",
        steps=(RecoveryStep(
            step_id="inspect-wlm", action="Inspect WLM queues",
            purpose="Diagnose contention", risk="low", requires_approval=False,
        ),),
    )


def test_recovery_llm_is_advisory_only(monkeypatch):
    monkeypatch.setenv("SENTINELOPS_RECOVERY_LLM_ENABLED", "true")
    monkeypatch.setenv("SENTINELOPS_LLM_ENABLED", "true")
    monkeypatch.setattr("agents.recovery.build_recovery_plan", lambda state: _plan())
    monkeypatch.setattr("agents.llm.ask", lambda *args, **kwargs: "Execute an unsafe action now.")
    state = {"incident_id": "RS-001", "findings": [], "messages": [],
             "adjudication": SimpleNamespace(brief_explanation="WLM contention")}
    result = run_recovery_agent(state)
    assert result["recovery_plan"] == _plan()
    assert evaluate_recovery_safety(result["recovery_plan"]).decision == "blocked"
    assert any(f.agent == "recovery_llm" for f in result["findings"])


def test_recovery_llm_can_be_disabled(monkeypatch):
    monkeypatch.setenv("SENTINELOPS_RECOVERY_LLM_ENABLED", "false")
    monkeypatch.setattr("agents.recovery.build_recovery_plan", lambda state: _plan())
    result = run_recovery_agent({"incident_id": "RS-001", "findings": [], "messages": []})
    assert not any(f.agent == "recovery_llm" for f in result["findings"])
