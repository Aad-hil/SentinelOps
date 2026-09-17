from rag.retrieval import KnowledgeRetriever, RetrievalResult


def search_knowledge(
    retriever: KnowledgeRetriever,
    query: str,
    *,
    top_k: int = 5,
) -> list[RetrievalResult]:
    """Search the SentinelOps knowledge corpus through the RAG retriever."""
    return retriever.retrieve(query, top_k=top_k)
