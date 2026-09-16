from pathlib import Path

import pytest

from rag.ingestion import infer_category, load_markdown_documents


KNOWLEDGE_ROOT = Path(__file__).parents[1] / "knowledge"


def test_loads_all_markdown_documents():
    documents = load_markdown_documents(KNOWLEDGE_ROOT)

    assert len(documents) == 14
    assert all(document.content for document in documents)
    assert all(document.source.endswith(".md") for document in documents)


def test_documents_are_sorted_deterministically():
    documents = load_markdown_documents(KNOWLEDGE_ROOT)
    sources = [document.source for document in documents]

    assert sources == sorted(sources)


def test_category_comes_from_knowledge_directory():
    documents = load_markdown_documents(KNOWLEDGE_ROOT)
    categories = {document.category for document in documents}

    assert categories == {"architecture", "deployment", "incidents", "runbooks"}


def test_metadata_preserves_filename_and_path():
    documents = load_markdown_documents(KNOWLEDGE_ROOT)
    document = next(
        item for item in documents if item.source.endswith("database-high-cpu.md")
    )

    assert document.metadata["filename"] == "database-high-cpu.md"
    assert document.metadata["path"] == document.source


def test_infer_category_for_root_file():
    root = Path("knowledge")
    assert infer_category(root / "notes.md", root) == "uncategorized"


def test_missing_knowledge_directory():
    with pytest.raises(FileNotFoundError):
        load_markdown_documents("does-not-exist")


def test_non_directory_knowledge_path(tmp_path):
    file_path = tmp_path / "knowledge.md"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        load_markdown_documents(file_path)
