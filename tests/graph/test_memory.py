from langgraph.checkpoint.memory import MemorySaver

from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence


def test_graph_can_persist_short_term_state_by_thread():
    evidence = build_incident_002_evidence()
    checkpointer = MemorySaver()
    graph = build_investigation_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": evidence.incident.incident_id}}

    result = graph.invoke(
        {
            "incident_id": evidence.incident.incident_id,
            "incident_summary": evidence.incident.description,
            "evidence": evidence,
        },
        config=config,
    )

    saved = graph.get_state(config)

    assert result["investigation_status"] == "awaiting_human_approval"
    assert saved.values["incident_id"] == "INC-002"
    assert saved.values["investigation_status"] == "awaiting_human_approval"
    assert saved.values["completed_tasks"][-1] == "safety"


def test_checkpoint_threads_are_isolated():
    evidence = build_incident_002_evidence()
    checkpointer = MemorySaver()
    graph = build_investigation_graph(checkpointer=checkpointer)
    config_a = {"configurable": {"thread_id": "INC-002-A"}}
    config_b = {"configurable": {"thread_id": "INC-002-B"}}

    graph.invoke(
        {
            "incident_id": "INC-002-A",
            "incident_summary": evidence.incident.description,
            "evidence": evidence,
        },
        config=config_a,
    )

    assert graph.get_state(config_a).values["incident_id"] == "INC-002-A"
    assert graph.get_state(config_b).values == {}
