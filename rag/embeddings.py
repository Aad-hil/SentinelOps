"""Embedding providers for SentinelOps retrieval."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Protocol

DEFAULT_MODEL_ID = "amazon.titan-embed-text-v2:0"
DEFAULT_DIMENSIONS = 1024
DEFAULT_REGION = "ap-south-1"


class EmbeddingProvider(Protocol):
    """Interface implemented by all SentinelOps embedding backends."""

    dimension: int

    def embed_text(self, text: str) -> list[float]:
        """Embed one text value."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple text values."""


class BedrockEmbeddingProvider:
    """Generate embeddings with Amazon Titan Text Embeddings V2."""

    def __init__(
        self,
        *,
        region_name: str = DEFAULT_REGION,
        model_id: str = DEFAULT_MODEL_ID,
        dimensions: int = DEFAULT_DIMENSIONS,
        normalize: bool = True,
        client: Any | None = None,
    ) -> None:
        if dimensions not in {256, 512, 1024}:
            raise ValueError("dimensions must be one of 256, 512, or 1024")
        if not model_id:
            raise ValueError("model_id cannot be empty")
        if not region_name:
            raise ValueError("region_name cannot be empty")

        self.region_name = region_name
        self.model_id = model_id
        self.dimension = dimensions
        self.normalize = normalize

        if client is None:
            import boto3

            client = boto3.client("bedrock-runtime", region_name=region_name)
        self._client = client

    def embed_text(self, text: str) -> list[float]:
        """Generate one normalized float embedding through Bedrock."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        request_body = json.dumps(
            {
                "inputText": text,
                "dimensions": self.dimension,
                "normalize": self.normalize,
            }
        )
        response = self._client.invoke_model(
            modelId=self.model_id,
            body=request_body,
            contentType="application/json",
            accept="application/json",
        )
        body = response["body"].read()
        payload = json.loads(body)
        embedding = payload.get("embedding")
        if not isinstance(embedding, list):
            raise ValueError("Bedrock response did not contain an embedding")
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Expected {self.dimension} dimensions, got {len(embedding)}"
            )
        return [float(value) for value in embedding]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed documents in deterministic input order.

        Titan Text Embeddings V2 is invoked once per text here. This keeps the
        provider simple and observable for the small SentinelOps corpus; batch
        or async optimization can be added later without changing the public
        interface.
        """
        return [self.embed_text(text) for text in texts]
