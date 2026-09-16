from qdrant_client import QdrantClient

from rag.chunking import DocumentChunk
from rag.vector_store import QdrantVectorStore, stable_point_id


def make_chunk(index: int) -> DocumentChunk:
    return DocumentChunk(
        content=f"Evidence content {index}",
        source="knowledge/runbooks/example.md",
        category="runbooks",
        chunk_id=f"knowledge/runbooks/example.md::chunk-{index}",
        metadata={"chunk_index": str(index)},
    )


def test_stable_point_id_is_deterministic():
    first = stable_point_id("example::chunk-1")
    second = stable_point_id("example::chunk-1")

    assert first == second
    assert len(first) == 36
    assert first.count("-") == 4


def test_upsert_and_search_with_in_memory_qdrant():
    client = QdrantClient(":memory:")
    store = QdrantVectorStore(
        client=client,
        collection_name="test_knowledge",
        dimension=3,
    )
    chunks = [make_chunk(0), make_chunk(1)]
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

    assert store.upsert_chunks(chunks, embeddings) == 2

    results = store.search([1.0, 0.0, 0.0], limit=1)

    assert len(results) == 1
    assert results[0].payload["chunk_id"] == chunks[0].chunk_id


def test_upsert_requires_matching_counts():
    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="test_knowledge",
        dimension=3,
    )

    try:
        store.upsert_chunks([make_chunk(0)], [])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("Expected mismatched lengths to fail")


def test_search_rejects_wrong_dimension():
    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="test_knowledge",
        dimension=3,
    )

    try:
        store.search([1.0, 0.0], limit=1)
    except ValueError as exc:
        assert "Expected 3 dimensions" in str(exc)
    else:
        raise AssertionError("Expected wrong query dimension to fail")
