"""Exercise actual LangGraph interrupt/resume against a safety-approved fixture.

RS-001 itself is evidence-insufficient and must remain blocked.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from graph.state import InvestigationState
from recovery.models import RecoveryPlan, RecoveryStep
from safety.human_checkpoint import run_human_approval_checkpoint
from safety.policy import evaluate_recovery_safety


def _approval_graph():
    graph = StateGraph(InvestigationState)
    graph.add_node("human_approval", run_human_approval_checkpoint)
    graph.add_edge(START, "human_approval")
    graph.add_edge("human_approval", END)
    return graph.compile(checkpointer=MemorySaver())


def _reviewable_state():
    plan = RecoveryPlan(
        incident_id="RS-001",
        hypothesis_id="RSH1",
        confidence=0.90,
        readiness="ready_for_review",
        rationale="Controlled test fixture with verified evidence.",
        steps=(
            RecoveryStep(
                step_id="inspect-wlm",
                action="Inspect Redshift WLM queues.",
                purpose="Validate queue contention.",
                risk="low",
                requires_approval=False,
                evidence=("test:queue-observation",),
            ),
            RecoveryStep(
                step_id="adjust-wlm",
                action="Prepare reversible WLM adjustment for operator review.",
                purpose="Mitigate contention only after approval.",
                risk="medium",
                requires_approval=True,
                evidence=("test:verified-causal-chain",),
            ),
        ),
    )
    safety = evaluate_recovery_safety(plan)
    assert safety.human_approval_required
    return {
        "incident_id": "RS-001",
        "recovery_plan": plan,
        "safety_decision": safety,
        "investigation_status": "awaiting_human_approval",
        "approval_status": "pending",
        "approval_required": True,
    }


def test_human_approval_checkpoint_interrupts_and_resumes():
    graph = _approval_graph()
    config = {"configurable": {"thread_id": "approval-test-1"}}
    paused = graph.invoke(_reviewable_state(), config=config)
    assert paused["investigation_status"] == "awaiting_human_approval"
    assert paused["approval_required"] is True
    assert paused["approval_status"] == "pending"
    assert graph.get_state(config).interrupts

    completed = graph.invoke(
        Command(resume={"approved": True, "reviewer": "operator-1"}),
        config=config,
    )
    assert completed["approval_status"] == "approved"
    assert completed["approval_required"] is False
    assert completed["investigation_status"] == "approved_for_execution"


def test_human_rejection_resumes_to_blocked_state():
    graph = _approval_graph()
    config = {"configurable": {"thread_id": "approval-test-2"}}
    graph.invoke(_reviewable_state(), config=config)
    blocked = graph.invoke(
        Command(resume={"approved": False, "reviewer": "operator-1"}),
        config=config,
    )
    assert blocked["approval_status"] == "rejected"
    assert blocked["approval_required"] is False
    assert blocked["investigation_status"] == "blocked"
