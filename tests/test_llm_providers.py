"""Offline tests for hosted Groq and local Ollama inference."""
import json
from io import BytesIO
from unittest.mock import patch

from agents import llm


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_groq_uses_hosted_api_and_bearer_token():
    calls = []

    def fake_open(request, timeout):
        calls.append((request, timeout))
        return FakeResponse(json.dumps({"choices": [{"message": {"content": "Grounded answer"}}]}).encode())

    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "SENTINELOPS_LLM_MODEL": "llama-3.3-70b-versatile",
        "GROQ_API_KEY": "fake-test-key",
    }), patch.object(llm, "urlopen", side_effect=fake_open):
        assert llm.ask("System", "Evidence") == "Grounded answer"

    request, _ = calls[0]
    assert request.full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer fake-test-key"
    payload = json.loads(request.data)
    assert payload["stream"] is False


def test_groq_missing_key_fails_closed():
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "GROQ_API_KEY": "",
    }), patch.object(llm, "urlopen") as call:
        assert llm.ask("System", "Evidence") is None
        call.assert_not_called()


def test_ollama_remains_available():
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "ollama",
        "SENTINELOPS_LLM_MODEL": "qwen3:4b",
    }), patch.object(llm, "urlopen", return_value=FakeResponse(
        b'{"message":{"content":"Local response"}}'
    )):
        assert llm.ask("System", "Evidence") == "Local response"
