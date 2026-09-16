from dataclasses import dataclass, field
import re

from rag.models import Document


@dataclass(frozen=True)
class DocumentChunk:
    """A retrieval-ready chunk derived from a source document."""

    content: str
    source: str
    category: str
    chunk_id: str
    metadata: dict[str, str] = field(default_factory=dict)


_HEADING_RE = re.compile(r"^#{1,6}\s+.+$")


def _split_markdown_sections(content: str) -> list[str]:
    """Split Markdown at headings while keeping each heading with its section."""

    sections: list[str] = []
    current: list[str] = []

    for line in content.splitlines():
        if _HEADING_RE.match(line.strip()) and current:
            section = "\n".join(current).strip()
            if section:
                sections.append(section)
            current = []
        current.append(line)

    section = "\n".join(current).strip()
    if section:
        sections.append(section)

    return sections


def _split_long_section(section: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split an oversized section on paragraph boundaries, then words if needed."""

    if len(section) <= chunk_size:
        return [section]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", section) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())

        if len(paragraph) <= chunk_size:
            overlap = chunks[-1][-chunk_overlap:] if chunks and chunk_overlap else ""
            current = f"{overlap}\n\n{paragraph}".strip() if overlap else paragraph
            if len(current) > chunk_size:
                current = ""
                chunks.extend(_split_words(paragraph, chunk_size, chunk_overlap))
        else:
            chunks.extend(_split_words(paragraph, chunk_size, chunk_overlap))
            current = ""

    if current:
        chunks.append(current.strip())

    return chunks


def _split_words(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current_words: list[str] = []

    for word in words:
        candidate = " ".join([*current_words, word])
        if current_words and len(candidate) > chunk_size:
            chunks.append(" ".join(current_words))
            overlap_text = chunks[-1][-chunk_overlap:] if chunk_overlap else ""
            current_words = overlap_text.split() if overlap_text else []
        current_words.append(word)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


def chunk_document(
    document: Document,
    *,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[DocumentChunk]:
    """Create deterministic Markdown-aware chunks from a source document."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    # A small test/custom chunk size can legitimately be smaller than the
    # default overlap. In that case, use the largest valid overlap instead of
    # failing an otherwise valid chunking request.
    effective_overlap = min(chunk_overlap, max(0, chunk_size - 1))

    sections = _split_markdown_sections(document.content)
    chunks: list[DocumentChunk] = []

    for section in sections:
        chunks.extend(
            DocumentChunk(
                content=content,
                source=document.source,
                category=document.category,
                chunk_id=f"{document.source}::chunk-{index}",
                metadata={
                    **document.metadata,
                    "chunk_index": str(index),
                },
            )
            for index, content in enumerate(
                _split_long_section(section, chunk_size, effective_overlap)
            )
        )

    # Re-index globally because a document can produce multiple sections.
    return [
        DocumentChunk(
            content=chunk.content,
            source=chunk.source,
            category=chunk.category,
            chunk_id=f"{document.source}::chunk-{index}",
            metadata={**chunk.metadata, "chunk_index": str(index)},
        )
        for index, chunk in enumerate(chunks)
    ]


def chunk_documents(
    documents: list[Document],
    *,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[DocumentChunk]:
    """Chunk a collection of documents while preserving source order."""

    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return chunks
