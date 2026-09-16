from dataclasses import dataclass

from rag.indexer import index_knowledge


@dataclass
class FakeProvider:
    dimension: int = 3

    def embed_documents(self, texts):
        return [[float(index), 0.0, 1.0] for index, _ in enumerate(texts)]


class FakeStore:
    collection_name = "test_collection"

    def __init__(self):
        self.calls = []

    def upsert_chunks(self, chunks, embeddings):
        self.calls.append((chunks, embeddings))
        return len(chunks)


def test_index_knowledge_connects_ingestion_chunking_embedding_and_storage(
    tmp_path,
):
    knowledge = tmp_path / "knowledge"
    runbooks = knowledge / "runbooks"
    runbooks.mkdir(parents=True)
    (runbooks / "database.md").write_text(
        "# Database\n\nCheck CPU and query latency.", encoding="utf-8"
    )
    (runbooks / "rollback.md").write_text(
        "# Rollback\n\nRollback the deployment safely.", encoding="utf-8"
    )

    provider = FakeProvider()
    store = FakeStore()

    result = index_knowledge(
        knowledge_root=knowledge,
        embedding_provider=provider,
        vector_store=store,
    )

    assert result.documents == 2
    assert result.chunks == 2
    assert result.vectors == 2
    assert result.collection == "test_collection"
    assert len(store.calls) == 1
    chunks, embeddings = store.calls[0]
    assert [chunk.source for chunk in chunks] == [
        "runbooks/database.md",
        "runbooks/rollback.md",
    ]
    assert len(embeddings) == 2
    assert all(len(embedding) == 3 for embedding in embeddings)
