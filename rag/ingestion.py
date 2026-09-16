from pathlib import Path

from rag.models import Document

SUPPORTED_SUFFIXES = {".md"}


def infer_category(path: Path, root: Path) -> str:
    """Infer a document category from its first directory below the root."""

    relative = path.relative_to(root)
    if len(relative.parts) < 2:
        return "uncategorized"
    return relative.parts[0]


def load_markdown_documents(root: str | Path = "knowledge") -> list[Document]:
    """Load Markdown knowledge documents in deterministic path order."""

    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Knowledge directory does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Knowledge path is not a directory: {root_path}")

    documents: list[Document] = []

    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        source = path.as_posix()
        documents.append(
            Document(
                content=content,
                source=source,
                category=infer_category(path, root_path),
                metadata={
                    "filename": path.name,
                    "path": source,
                },
            )
        )

    return documents
