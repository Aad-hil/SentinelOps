"""Offline tests for hosted Groq SDK and local Ollama inference."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from agents import llm


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_groq_uses_sdk_and_configured_model():
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Grounded answer"))])
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "SENTINELOPS_LLM_MODEL": "openai/gpt-oss-20b",
        "GROQ_API_KEY": "fake-test-key",
    }), patch("groq.Groq") as client_class:
        client_class.return_value.chat.completions.create.return_value = response
        assert llm.ask("System", "Evidence") == "Grounded answer"
        client_class.assert_called_once()
        kwargs = client_class.return_value.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "openai/gpt-oss-20b"
        assert kwargs["messages"][0]["role"] == "system"


def test_groq_missing_key_fails_closed():
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "GROQ_API_KEY": "",
    }), patch("groq.Groq") as client_class:
        assert llm.ask("System", "Evidence") is None
        client_class.assert_not_called()


def test_groq_sdk_error_fails_closed():
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "GROQ_API_KEY": "fake-test-key",
    }), patch("groq.Groq") as client_class:
        client_class.return_value.chat.completions.create.side_effect = RuntimeError("test failure")
        assert llm.ask("System", "Evidence") is None


def test_ollama_remains_available():
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "ollama",
        "SENTINELOPS_LLM_MODEL": "qwen3:4b",
    }), patch.object(llm, "urlopen", return_value=FakeResponse(
        b'{"message":{"content":"Local response"}}'
    )):
        assert llm.ask("System", "Evidence") == "Local response"
