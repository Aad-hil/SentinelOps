from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.adjudication import run_adjudication_agent
from agents.critic import run_critic_agent
from agents.deployment import run_deployment_agent
from agents.knowledge import run_knowledge_agent
from agents.root_cause import run_root_cause_agent
from agents.recovery import run_recovery_agent
from agents.safety import run_safety_agent
from agents.supervisor import run_supervisor
from agents.telemetry import run_telemetry_agent
from graph.state import InvestigationState
from memory.retrieval import retrieve_historical_incidents
from safety.human_checkpoint import run_human_approval_checkpoint


def _route_after_supervisor(state: InvestigationState) -> str:
    """Route the supervisor decision to the next investigation node."""
    return state.get("next_agent", "complete")


def _build_historical_memory_node(repository: Any):
    """Create a graph node that retrieves prior incidents without checkpointing the client."""
    def retrieve_history(state: InvestigationState) -> dict[str, Any]:
        if repository is None:
            return {
                "historical_incidents": [],
                "messages": list(state.get("messages", [])) + [
                    "Historical incident retrieval is not configured."
                ],
            }

        query = f"{state['evidence'].incident.title}. {state['evidence'].incident.description}"
        matches = retrieve_historical_incidents(
            repository,
            query,
            limit=3,
            exclude_incident_id=state["incident_id"],
        )
        return {
            "historical_incidents": matches,
            "messages": list(state.get("messages", [])) + [
                f"Historical memory retrieved {len(matches)} relevant prior incidents."
            ],
        }

    return retrieve_history


def _skip_human_approval_checkpoint(state: InvestigationState) -> dict[str, Any]:
    """Preserve non-checkpoint graph tests and dry runs without an interrupt."""
    return {}


def build_investigation_graph(
    checkpointer: Any = None,
    incident_memory_repository: Any = None,
):
    """Build the investigation graph with optional short-term and historical memory."""
    graph = StateGraph(InvestigationState)
    graph.add_node("historical_memory", _build_historical_memory_node(incident_memory_repository))
    graph.add_node("supervisor", run_supervisor)
    graph.add_node("telemetry", run_telemetry_agent)
    graph.add_node("knowledge", run_knowledge_agent)
    graph.add_node("deployment", run_deployment_agent)
    graph.add_node("root_cause", run_root_cause_agent)
    graph.add_node("critic", run_critic_agent)
    graph.add_node("adjudication", run_adjudication_agent)
    graph.add_node("recovery", run_recovery_agent)
    graph.add_node("safety", run_safety_agent)
    graph.add_node(
        "human_approval",
        run_human_approval_checkpoint if checkpointer is not None else _skip_human_approval_checkpoint,
    )

    graph.add_edge(START, "historical_memory")
    graph.add_edge("historical_memory", "supervisor")
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
            "recovery": "recovery",
            "safety": "safety",
            "complete": END,
        },
    )
    graph.add_edge("telemetry", "supervisor")
    graph.add_edge("knowledge", "supervisor")
    graph.add_edge("deployment", "supervisor")
    graph.add_edge("root_cause", "supervisor")
    graph.add_edge("critic", "supervisor")
    graph.add_edge("adjudication", "supervisor")
    graph.add_edge("recovery", "supervisor")
    graph.add_edge("safety", "human_approval")
    graph.add_edge("human_approval", "supervisor")

    return graph.compile(checkpointer=checkpointer)
