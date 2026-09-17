from datetime import datetime, timezone

from qdrant_client import QdrantClient

from memory.models import IncidentMemory
from memory.semantic import QdrantIncidentMemoryRepository


class FakeEmbeddingProvider:
    dimension = 3

    def __init__(self):
        self.texts = []

    def embed_text(self, text: str) -> list[float]:
        self.texts.append(text)
        if "database" in text.lower():
            return [1.0, 0.0, 0.0]
        return [0.0, 1.0, 0.0]

    def embed_documents(self, texts):
        return [self.embed_text(text) for text in texts]


def make_memory() -> IncidentMemory:
    return IncidentMemory(
        incident_id="INC-002",
        service="github-web",
        severity="HIGH",
        title="Primary database saturation after deployment",
        description="Database saturation caused elevated update errors.",
        root_cause_hypothesis_id="H1",
        root_cause_statement="A deployment caused primary database saturation.",
        root_cause_confidence=0.95,
        resolution_summary="The problematic deployment was rolled back.",
        recovery_action="Rollback deployment and verify recovery.",
        created_at=datetime(2025, 1, 9, 1, 26, tzinfo=timezone.utc),
        completed_at=datetime(2025, 1, 9, 1, 56, tzinfo=timezone.utc),
    )


def test_index_and_search_with_in_memory_qdrant():
    provider = FakeEmbeddingProvider()
    client = QdrantClient(":memory:")
    repository = QdrantIncidentMemoryRepository(
        embedding_provider=provider,
        client=client,
        collection_name="test_incidents",
    )

    repository.index(make_memory())
    results = repository.search("database saturation after deployment", limit=1)

    assert len(results) == 1
    assert results[0].payload["incident_id"] == "INC-002"
    assert results[0].payload["root_cause_hypothesis_id"] == "H1"
    assert "root cause:" in results[0].payload["search_text"]
    assert provider.texts[0].startswith("Primary database saturation")


def test_index_is_idempotent_for_same_incident():
    provider = FakeEmbeddingProvider()
    client = QdrantClient(":memory:")
    repository = QdrantIncidentMemoryRepository(
        embedding_provider=provider,
        client=client,
        collection_name="test_incidents",
    )

    repository.index(make_memory())
    repository.index(make_memory())

    count = client.count(collection_name="test_incidents").count
    assert count == 1


def test_search_validates_query_and_limit():
    repository = QdrantIncidentMemoryRepository(
        embedding_provider=FakeEmbeddingProvider(),
        client=QdrantClient(":memory:"),
        collection_name="test_incidents",
    )

    cases = [
        ("", 5, "non-empty"),
        ("database", 0, "greater than zero"),
    ]
    for query, limit, expected in cases:
        try:
            repository.search(query, limit=limit)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("Expected validation to fail")
