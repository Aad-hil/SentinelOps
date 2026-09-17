from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.adjudication import run_adjudication_agent
from agents.critic import run_critic_agent
from agents.deployment import run_deployment_agent
from agents.knowledge import run_knowledge_agent
from agents.root_cause import run_root_cause_agent
from agents.supervisor import run_supervisor
from agents.telemetry import run_telemetry_agent
from graph.state import InvestigationState


def _route_after_supervisor(state: InvestigationState) -> str:
    """Route the supervisor decision to the next investigation node."""
    return state.get("next_agent", "complete")


def build_investigation_graph(checkpointer: Any = None):
    """Build the investigation graph with optional short-term state memory."""
    graph = StateGraph(InvestigationState)
    graph.add_node("supervisor", run_supervisor)
    graph.add_node("telemetry", run_telemetry_agent)
    graph.add_node("knowledge", run_knowledge_agent)
    graph.add_node("deployment", run_deployment_agent)
    graph.add_node("root_cause", run_root_cause_agent)
    graph.add_node("critic", run_critic_agent)
    graph.add_node("adjudication", run_adjudication_agent)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "telemetry": "telemetry",
            "knowledge": "knowledge",
            "deployment": "deployment",
            "root_cause": "root_cause",
            "critic": "critic",
            "adjudication": "adjudication",
            "complete": END,
        },
    )
    graph.add_edge("telemetry", "supervisor")
    graph.add_edge("knowledge", "supervisor")
    graph.add_edge("deployment", "supervisor")
    graph.add_edge("root_cause", "supervisor")
    graph.add_edge("critic", "supervisor")
    graph.add_edge("adjudication", "supervisor")

    return graph.compile(checkpointer=checkpointer)
