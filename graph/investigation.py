from langgraph.graph import END, START, StateGraph

from agents.deployment import run_deployment_agent
from agents.knowledge import run_knowledge_agent
from agents.root_cause import run_root_cause_agent
from agents.supervisor import run_supervisor
from agents.telemetry import run_telemetry_agent
from graph.state import InvestigationState


def _route_after_supervisor(state: InvestigationState) -> str:
    """Route the supervisor decision to the next investigation node."""
    return state.get("next_agent", "complete")


def build_investigation_graph():
    """Build the evidence-collection and hypothesis-evaluation graph."""
    graph = StateGraph(InvestigationState)
    graph.add_node("supervisor", run_supervisor)
    graph.add_node("telemetry", run_telemetry_agent)
    graph.add_node("knowledge", run_knowledge_agent)
    graph.add_node("deployment", run_deployment_agent)
    graph.add_node("root_cause", run_root_cause_agent)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "telemetry": "telemetry",
            "knowledge": "knowledge",
            "deployment": "deployment",
            "root_cause": "root_cause",
            "complete": END,
        },
    )
    graph.add_edge("telemetry", "supervisor")
    graph.add_edge("knowledge", "supervisor")
    graph.add_edge("deployment", "supervisor")
    graph.add_edge("root_cause", "supervisor")

    return graph.compile()
