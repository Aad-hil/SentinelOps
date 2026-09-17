from rag.retrieval import RetrievalResult
from tools.knowledge import search_knowledge


class FakeRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        self.calls.append((query, top_k))
        return [
            RetrievalResult(
                content="Database query latency runbook.",
                source="runbooks/database-query-latency.md",
                category="runbook",
                chunk_id="database-query-latency:0",
                score=0.91,
                metadata={"path": "runbooks/database-query-latency.md"},
            )
        ]


def test_search_knowledge_delegates_to_rag_retriever():
    retriever = FakeRetriever()

    results = search_knowledge(retriever, "database query latency", top_k=3)

    assert retriever.calls == [("database query latency", 3)]
    assert results[0].source == "runbooks/database-query-latency.md"
