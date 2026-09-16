from rag.chunking import chunk_document, chunk_documents
from rag.ingestion import load_markdown_documents
from rag.models import Document


def test_chunking_preserves_source_and_category():
    document = Document(
        content="# Database CPU\n\nInvestigate sustained CPU saturation.",
        source="knowledge/runbooks/database-high-cpu.md",
        category="runbooks",
        metadata={"filename": "database-high-cpu.md"},
    )

    chunks = chunk_document(document, chunk_size=100)

    assert len(chunks) == 1
    assert chunks[0].content.startswith("# Database CPU")
    assert chunks[0].source == document.source
    assert chunks[0].category == document.category
    assert chunks[0].chunk_id.endswith("::chunk-0")
    assert chunks[0].metadata["chunk_index"] == "0"


def test_oversized_content_is_split_within_limit():
    document = Document(
        content="# Runbook\n\n" + "word " * 300,
        source="knowledge/runbooks/example.md",
        category="runbooks",
    )

    chunks = chunk_document(document, chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 100 for chunk in chunks)
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == [
        str(index) for index in range(len(chunks))
    ]


def test_chunk_ids_are_deterministic():
    document = Document(
        content="# A\n\nalpha\n\n# B\n\nbeta",
        source="knowledge/runbooks/example.md",
        category="runbooks",
    )

    first = chunk_document(document, chunk_size=50)
    second = chunk_document(document, chunk_size=50)

    assert first == second


def test_chunk_documents_preserves_document_order():
    documents = load_markdown_documents("knowledge")

    chunks = chunk_documents(documents, chunk_size=900, chunk_overlap=120)

    assert chunks
    assert chunks[0].source == documents[0].source
    assert chunks[-1].source == documents[-1].source


def test_invalid_chunk_parameters():
    document = Document(content="content", source="x.md", category="runbooks")

    for kwargs in ({"chunk_size": 0}, {"chunk_size": 10, "chunk_overlap": -1}, {"chunk_size": 10, "chunk_overlap": 10}):
        try:
            chunk_document(document, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError for invalid chunk parameters")
