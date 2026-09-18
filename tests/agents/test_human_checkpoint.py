from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence


def _initial_state():
    evidence = build_incident_002_evidence()
    return {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }


def test_human_approval_checkpoint_interrupts_and_resumes():
    graph = build_investigation_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "approval-test-1"}}

    paused = graph.invoke(_initial_state(), config=config)

    assert paused["investigation_status"] == "awaiting_human_approval"
    assert paused["approval_required"] is True
    assert paused["approval_status"] == "pending"
    snapshot = graph.get_state(config)
    assert snapshot.interrupts

    completed = graph.invoke(
        Command(resume={"approved": True, "reviewer": "operator-1"}),
        config=config,
    )

    assert completed["approval_status"] == "approved"
    assert completed["approval_required"] is False
    assert completed["investigation_status"] == "approved_for_execution"


def test_human_rejection_resumes_to_blocked_state():
    graph = build_investigation_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "approval-test-2"}}

    graph.invoke(_initial_state(), config=config)
    blocked = graph.invoke(
        Command(resume={"approved": False, "reviewer": "operator-1"}),
        config=config,
    )

    assert blocked["approval_status"] == "rejected"
    assert blocked["approval_required"] is False
    assert blocked["investigation_status"] == "blocked"
