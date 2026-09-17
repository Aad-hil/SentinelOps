from graph.state import AgentFinding, InvestigationState, append_finding
from tools.knowledge import search_knowledge


def run_knowledge_agent(state: InvestigationState) -> dict:
    """Search the knowledge corpus through the agent's RAG tool.

    The retriever is injected through state so tests and future graph wiring can
    provide either a real Bedrock/Qdrant retriever or a deterministic fake.
    """

    evidence = state["evidence"]
    retriever = state.get("knowledge_retriever")
    query = f"{evidence.incident.title}. {evidence.incident.description}"

    if retriever is None:
        summary = "Knowledge Agent could not search the RAG corpus because no retriever was provided."
        finding = AgentFinding(
            agent="knowledge",
            category="knowledge",
            summary=summary,
            evidence=(),
            confidence=0.2,
        )
        return append_finding(state, finding)

    results = search_knowledge(retriever, query, top_k=5)
    sources = tuple(dict.fromkeys(result.source for result in results))
    summary = (
        "Knowledge Agent retrieved relevant knowledge sources: "
        + (", ".join(sources) if sources else "no matching sources")
    )

    finding = AgentFinding(
        agent="knowledge",
        category="knowledge",
        summary=summary,
        evidence=sources,
        confidence=0.7 if results else 0.3,
    )
    return append_finding(state, finding)
