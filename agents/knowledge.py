from graph.state import AgentFinding, InvestigationState, append_finding


_RUNBOOK_HINTS = {
    "database": ("database-high-cpu.md", "database-query-latency.md"),
    "query": ("database-query-latency.md",),
    "deploy": ("deployment-validation.md", "deployment-rollback.md"),
    "rollback": ("deployment-rollback.md",),
}


def run_knowledge_agent(state: InvestigationState) -> dict:
    """Select relevant knowledge sources from the indexed corpus metadata.

    This first agent version deliberately does not call the LLM. It establishes
    the multi-agent contract while reusing the RAG corpus deterministically.
    """

    incident = state["evidence"].incident
    query = f"{incident.title} {incident.description}".lower()
    sources: list[str] = []

    for keyword, hints in _RUNBOOK_HINTS.items():
        if keyword in query:
            sources.extend(hints)

    sources = list(dict.fromkeys(sources))
    summary = (
        "Knowledge Agent identified relevant runbooks for the incident: "
        + (", ".join(sources) if sources else "no deterministic runbook match")
    )

    finding = AgentFinding(
        agent="knowledge",
        category="knowledge",
        summary=summary,
        evidence=tuple(sources),
        confidence=0.65 if sources else 0.35,
    )
    return append_finding(state, finding)
