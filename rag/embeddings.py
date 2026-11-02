"""Embedding providers for SentinelOps retrieval."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any, Protocol

DEFAULT_MODEL_ID = "amazon.titan-embed-text-v2:0"
DEFAULT_DIMENSIONS = 1024
DEFAULT_REGION = "ap-south-1"
DEFAULT_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingProvider(Protocol):
    """Interface implemented by all SentinelOps embedding backends."""

    dimension: int

    def embed_text(self, text: str) -> list[float]:
        """Embed one text value."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed multiple text values."""


class SentenceTransformerEmbeddingProvider:
    """Generate local embeddings without a paid API or cloud credentials."""

    def __init__(self, *, model_name: str = DEFAULT_LOCAL_MODEL, model: Any | None = None) -> None:
        if not model_name:
            raise ValueError("model_name cannot be empty")
        if model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_name)
        dimension = model.get_sentence_embedding_dimension()
        if not dimension:
            raise ValueError("The sentence-transformer model did not expose an embedding dimension")
        self.model_name = model_name
        self.dimension = int(dimension)
        self._model = model

    def embed_text(self, text: str) -> list[float]:
        """Embed one text value using the local model."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed texts in input order using a local sentence-transformer."""
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("all texts must be non-empty strings")
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector] for vector in vectors]


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
        """Embed documents in deterministic input order."""
        return [self.embed_text(text) for text in texts]


def create_embedding_provider_from_env() -> EmbeddingProvider:
    """Create the configured local or Bedrock embedding provider."""
    provider = os.getenv("SENTINELOPS_EMBEDDING_PROVIDER", "local").strip().lower()
    if provider == "local":
        return SentenceTransformerEmbeddingProvider(
            model_name=os.getenv("SENTINELOPS_LOCAL_EMBEDDING_MODEL", DEFAULT_LOCAL_MODEL)
        )
    if provider == "bedrock":
        return BedrockEmbeddingProvider(
            region_name=os.getenv("AWS_REGION", DEFAULT_REGION),
            model_id=os.getenv("BEDROCK_EMBEDDING_MODEL_ID", DEFAULT_MODEL_ID),
            dimensions=int(os.getenv("BEDROCK_EMBEDDING_DIMENSIONS", str(DEFAULT_DIMENSIONS))),
            normalize=os.getenv("BEDROCK_EMBEDDING_NORMALIZE", "true").lower() == "true",
        )
    raise ValueError("SENTINELOPS_EMBEDDING_PROVIDER must be 'local' or 'bedrock'")
