from graph.evidence import EvidenceItem
from graph.state import AgentFinding, InvestigationState, append_agent_evidence, append_finding
from tools.knowledge import search_knowledge


_RUNBOOK_HINTS = {
    "database": ("runbooks/database-high-cpu.md", "runbooks/database-query-latency.md"),
    "query": ("runbooks/database-query-latency.md",),
    "deploy": ("runbooks/deployment-validation.md", "runbooks/deployment-rollback.md"),
    "rollback": ("runbooks/deployment-rollback.md",),
}


def run_knowledge_agent(state: InvestigationState) -> dict:
    """Search knowledge and publish normalized evidence."""
    evidence = state["evidence"]
    retriever = state.get("knowledge_retriever")
    query = f"{evidence.incident.title}. {evidence.incident.description}"

    items: list[EvidenceItem] = []
    if retriever is not None:
        results = search_knowledge(retriever, query, top_k=5)
        sources = tuple(dict.fromkeys(result.source for result in results))
        for result in results:
            items.append(EvidenceItem(
                source=result.source,
                evidence_type="knowledge",
                observation=result.content,
                relevance=max(0.0, min(1.0, result.score)),
                agent="knowledge",
            ))
        confidence = 0.7 if results else 0.3
    else:
        lowered = query.lower()
        fallback: list[str] = []
        for keyword, hints in _RUNBOOK_HINTS.items():
            if keyword in lowered:
                fallback.extend(hints)
        sources = tuple(dict.fromkeys(fallback))
        for source in sources:
            items.append(EvidenceItem(
                source=source,
                evidence_type="knowledge_reference",
                observation=f"Relevant knowledge source selected: {source}",
                relevance=0.65,
                agent="knowledge",
            ))
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
    result = append_finding(state, finding)
    result.update(append_agent_evidence(state, items))
    return result
