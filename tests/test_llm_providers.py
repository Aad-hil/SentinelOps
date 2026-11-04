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


def test_groq_usage_capture():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"), finish_reason="length")],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=40, total_tokens=140),
    )
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "GROQ_API_KEY": "fake-test-key",
    }), patch("groq.Groq") as client_class:
        client_class.return_value.chat.completions.create.return_value = response
        token = llm.begin_usage_capture()
        try:
            assert llm.ask("System", "Evidence") == "Answer"
        finally:
            records = llm.end_usage_capture(token)
    assert records == [{
        "prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 140,
        "finish_reason": "length", "attempts": 1,
    }]


def test_groq_retries_rate_limit_once():
    from groq import RateLimitError
    from httpx import Request, Response

    request = Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    limited = RateLimitError(
        "rate limit", response=Response(429, request=request, headers={"retry-after": "0"})
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Recovered"), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=4, total_tokens=9),
    )
    with patch.dict("os.environ", {
        "SENTINELOPS_LLM_ENABLED": "true",
        "SENTINELOPS_LLM_PROVIDER": "groq",
        "SENTINELOPS_GROQ_MAX_RETRIES": "1",
        "GROQ_API_KEY": "fake-test-key",
    }), patch("groq.Groq") as client_class, patch.object(llm.time, "sleep") as sleep:
        create = client_class.return_value.chat.completions.create
        create.side_effect = [limited, response]
        assert llm.ask("System", "Evidence") == "Recovered"
        assert create.call_count == 2
        sleep.assert_called_once()
