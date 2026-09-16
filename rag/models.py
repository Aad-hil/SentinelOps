from dataclasses import dataclass, field


@dataclass(frozen=True)
class Document:
    """A normalized knowledge document before chunking or embedding."""

    content: str
    source: str
    category: str
    metadata: dict[str, str] = field(default_factory=dict)
