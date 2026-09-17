from graph.state import AgentFinding, InvestigationState, append_finding
from tools.knowledge import search_knowledge


_RUNBOOK_HINTS = {
    "database": ("runbooks/database-high-cpu.md", "runbooks/database-query-latency.md"),
    "query": ("runbooks/database-query-latency.md",),
    "deploy": ("runbooks/deployment-validation.md", "runbooks/deployment-rollback.md"),
    "rollback": ("runbooks/deployment-rollback.md",),
}


def run_knowledge_agent(state: InvestigationState) -> dict:
    """Search the knowledge corpus through the agent's RAG tool.

    A deterministic fallback preserves the graph's zero-dependency behavior
    when no retriever is injected. Production wiring can inject the real
    Bedrock/Qdrant retriever through ``knowledge_retriever``.
    """

    evidence = state["evidence"]
    retriever = state.get("knowledge_retriever")
    query = f"{evidence.incident.title}. {evidence.incident.description}"

    if retriever is not None:
        results = search_knowledge(retriever, query, top_k=5)
        sources = tuple(dict.fromkeys(result.source for result in results))
        confidence = 0.7 if results else 0.3
    else:
        lowered = query.lower()
        fallback: list[str] = []
        for keyword, hints in _RUNBOOK_HINTS.items():
            if keyword in lowered:
                fallback.extend(hints)
        sources = tuple(dict.fromkeys(fallback))
        confidence = 0.65 if sources else 0.35

    summary = (
        "Knowledge Agent retrieved relevant knowledge sources: "
        + (", ".join(sources) if sources else "no matching sources")
    )
    finding = AgentFinding(
        agent="knowledge",
        category="knowledge",
        summary=summary,
        evidence=sources,
        confidence=confidence,
    )
    return append_finding(state, finding)
