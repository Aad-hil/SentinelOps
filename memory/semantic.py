"""Semantic long-term incident memory backed by Qdrant."""

from __future__ import annotations

import os
import uuid
from typing import Any

from qdrant_client import QdrantClient, models

from memory.models import IncidentMemory
from rag.embeddings import BedrockEmbeddingProvider, EmbeddingProvider

DEFAULT_COLLECTION = "sentinelops_incidents"
DEFAULT_URL = "http://localhost:6333"


class QdrantIncidentMemoryRepository:
    """Index completed incidents and retrieve semantically similar history."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        client: QdrantClient | None = None,
        url: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or BedrockEmbeddingProvider(
            region_name=os.getenv("AWS_REGION", "ap-south-1"),
            model_id=os.getenv(
                "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
            ),
            dimensions=int(os.getenv("BEDROCK_EMBEDDING_DIMENSIONS", "1024")),
            normalize=os.getenv("BEDROCK_EMBEDDING_NORMALIZE", "true").lower()
            == "true",
        )
        self.collection_name = collection_name or os.getenv(
            "QDRANT_INCIDENT_COLLECTION", DEFAULT_COLLECTION
        )
        qdrant_url = url or os.getenv("QDRANT_URL", DEFAULT_URL)
        self.client = client or QdrantClient(qdrant_url)
        self.dimension = self.embedding_provider.dimension

    def initialize(self) -> None:
        """Create the incident-memory collection when it does not exist."""
        if self.client.collection_exists(collection_name=self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.dimension,
                distance=models.Distance.COSINE,
            ),
        )

    def index(self, memory: IncidentMemory) -> None:
        """Embed and upsert one completed incident memory."""
        text = memory.to_search_text()
        embedding = self.embedding_provider.embed_text(text)
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Expected {self.dimension} dimensions, got {len(embedding)}"
            )

        self.initialize()
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"sentinelops:{memory.incident_id}",
            )
        )
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "incident_id": memory.incident_id,
                        "service": memory.service,
                        "severity": memory.severity,
                        "title": memory.title,
                        "description": memory.description,
                        "root_cause_hypothesis_id": memory.root_cause_hypothesis_id,
                        "root_cause_statement": memory.root_cause_statement,
                        "root_cause_confidence": memory.root_cause_confidence,
                        "resolution_summary": memory.resolution_summary,
                        "recovery_action": memory.recovery_action,
                        "investigation_status": memory.investigation_status,
                        "approval_status": memory.approval_status,
                        "search_text": text,
                    },
                )
            ],
        )

    def search(self, query: str, *, limit: int = 5) -> list[Any]:
        """Return semantically similar historical incident points."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        self.initialize()
        query_embedding = self.embedding_provider.embed_text(query)
        if len(query_embedding) != self.dimension:
            raise ValueError(
                f"Expected {self.dimension} dimensions, got {len(query_embedding)}"
            )
        return self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
        ).points
