"""End-to-end graph smoke test without external services."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command

from graph.investigation import build_investigation_graph
from graph.state import InvestigationState
from recovery.models import RecoveryPlan, RecoveryStep
from safety.human_checkpoint import run_human_approval_checkpoint
from safety.policy import evaluate_recovery_safety
from simulator.redshift import build_redshift_evidence_bundle


def test_rs001_graph_respects_insufficient_evidence():
    evidence = build_redshift_evidence_bundle("RS-001")
    graph = build_investigation_graph(checkpointer=MemorySaver())
    state = graph.invoke({
        "incident_id": "RS-001",
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }, config={"configurable": {"thread_id": "fresh-rs001-safety"}})
    assert state["adjudication"].hypothesis_id == "RSH1"
    assert state["safety_decision"].decision == "blocked"
    assert state["investigation_status"] == "awaiting_human_approval"
    assert state["approval_required"] is True
    assert graph.get_state({"configurable": {"thread_id": "fresh-rs001-safety"}}).interrupts


def _approval_graph_and_state():
    plan = RecoveryPlan(
        incident_id="RS-001", hypothesis_id="RSH1", confidence=0.9,
        readiness="ready_for_review", rationale="Verified controlled fixture",
        steps=(RecoveryStep(
            step_id="adjust-wlm", action="Prepare reversible WLM adjustment for review.",
            purpose="Review, not execution", risk="medium", requires_approval=True,
        ),),
    )
    decision = evaluate_recovery_safety(plan)
    assert decision.human_approval_required
    builder = StateGraph(InvestigationState)
    builder.add_node("human_approval", run_human_approval_checkpoint)
    builder.add_edge(START, "human_approval")
    builder.add_edge("human_approval", END)
    return builder.compile(checkpointer=MemorySaver()), {
        "incident_id": "RS-001", "recovery_plan": plan,
        "safety_decision": decision, "approval_required": True,
        "approval_status": "pending", "investigation_status": "awaiting_human_approval",
    }


def test_approval_interrupt_and_resume():
    graph, state = _approval_graph_and_state()
    config = {"configurable": {"thread_id": "fresh-approval"}}
    paused = graph.invoke(state, config=config)
    assert paused["approval_status"] == "pending"
    assert graph.get_state(config).interrupts
    approved = graph.invoke(Command(resume={"approved": True, "reviewer": "operator"}), config=config)
    assert approved["approval_status"] == "approved"
    assert approved["investigation_status"] == "approved_for_handoff"


def test_rejection_interrupt_and_resume():
    graph, state = _approval_graph_and_state()
    config = {"configurable": {"thread_id": "fresh-rejection"}}
    graph.invoke(state, config=config)
    rejected = graph.invoke(Command(resume={"approved": False, "reviewer": "operator"}), config=config)
    assert rejected["approval_status"] == "rejected"
    assert rejected["investigation_status"] == "blocked"
