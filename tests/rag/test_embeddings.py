import io
import json

import pytest

from rag.embeddings import BedrockEmbeddingProvider


class FakeBedrockClient:
    def __init__(self, embedding):
        self.embedding = embedding
        self.calls = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "body": io.BytesIO(
                json.dumps(
                    {
                        "embedding": self.embedding,
                        "inputTextTokenCount": 3,
                    }
                ).encode("utf-8")
            )
        }


def test_bedrock_embedding_provider_builds_expected_request():
    client = FakeBedrockClient([0.1, 0.2, 0.3])
    provider = BedrockEmbeddingProvider(
        region_name="ap-south-1",
        model_id="test-model",
        dimensions=3,
        client=client,
    )

    # Dimensions outside the Titan-supported set are rejected by the provider,
    # so use the default-supported size for this request-shape test instead.
    client = FakeBedrockClient([0.1] * 1024)
    provider = BedrockEmbeddingProvider(
        region_name="ap-south-1",
        model_id="test-model",
        dimensions=1024,
        normalize=True,
        client=client,
    )
    embedding = provider.embed_text("database query latency")

    assert len(embedding) == 1024
    call = client.calls[0]
    assert call["modelId"] == "test-model"
    assert call["contentType"] == "application/json"
    assert call["accept"] == "application/json"
    assert json.loads(call["body"]) == {
        "inputText": "database query latency",
        "dimensions": 1024,
        "normalize": True,
    }


def test_embed_documents_preserves_order():
    client = FakeBedrockClient([0.5] * 256)
    provider = BedrockEmbeddingProvider(dimensions=256, client=client)

    embeddings = provider.embed_documents(["first", "second", "third"])

    assert len(embeddings) == 3
    assert len(client.calls) == 3
    assert [json.loads(call["body"])["inputText"] for call in client.calls] == [
        "first",
        "second",
        "third",
    ]


def test_empty_text_is_rejected():
    client = FakeBedrockClient([0.1] * 256)
    provider = BedrockEmbeddingProvider(dimensions=256, client=client)

    with pytest.raises(ValueError, match="non-empty"):
        provider.embed_text("   ")


def test_invalid_dimensions_are_rejected():
    with pytest.raises(ValueError, match="256, 512, or 1024"):
        BedrockEmbeddingProvider(dimensions=768, client=FakeBedrockClient([]))


def test_unexpected_embedding_dimension_is_rejected():
    client = FakeBedrockClient([0.1] * 255)
    provider = BedrockEmbeddingProvider(dimensions=256, client=client)

    with pytest.raises(ValueError, match="Expected 256 dimensions"):
        provider.embed_text("test")
