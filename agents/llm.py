"""Optional evidence-grounded inference via Groq SDK or local Ollama.

LLM text is advisory; deterministic scoring, safety and approval remain authoritative.
"""
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def provider() -> str:
    return os.getenv("SENTINELOPS_LLM_PROVIDER", "ollama").strip().lower()


def enabled() -> bool:
    return os.getenv("SENTINELOPS_LLM_ENABLED", "false").strip().lower() in ("1", "true", "yes")


def ask(system: str, user: str, *, max_tokens: int = 700) -> str | None:
    """Return advisory model text, or None if inference is unavailable."""
    if not enabled():
        return None

    model_provider = provider()
    limit = max(1, min(max_tokens, int(os.getenv("SENTINELOPS_LLM_MAX_TOKENS", "900"))))
    timeout = float(os.getenv("SENTINELOPS_LLM_TIMEOUT", "45"))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    if model_provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            logger.warning("Groq inference unavailable: GROQ_API_KEY is missing")
            return None
        try:
            from groq import Groq

            client = Groq(api_key=api_key, timeout=timeout, max_retries=0)
            response = client.chat.completions.create(
                model=os.getenv("SENTINELOPS_LLM_MODEL", "openai/gpt-oss-20b"),
                messages=messages,
                temperature=0,
                max_completion_tokens=limit,
            )
            content = response.choices[0].message.content
            return content.strip() or None if isinstance(content, str) else None
        except Exception as exc:
            logger.warning("Groq inference failed (%s): %s", type(exc).__name__, exc)
            return None

    if model_provider != "ollama":
        logger.warning("Unsupported LLM provider: %s", model_provider)
        return None

    host = os.getenv("SENTINELOPS_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    if not (host.startswith("http://localhost:") or host.startswith("http://127.0.0.1:")):
        logger.warning("Ollama URL must point to localhost")
        return None

    payload = {
        "model": os.getenv("SENTINELOPS_LLM_MODEL", "qwen3:4b"),
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": limit,
            "num_ctx": int(os.getenv("SENTINELOPS_LLM_CONTEXT", "1536")),
        },
    }
    request = Request(
        host + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
        content = data.get("message", {}).get("content", "")
        return content.strip()[:2400] or None if isinstance(content, str) else None
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, KeyError, IndexError) as exc:
        logger.warning("Ollama inference failed (%s): %s", type(exc).__name__, exc)
        return None


def evidence_context(state, *, limit: int = 10) -> str:
    """Only pass bounded observed evidence, not hidden ground-truth labels."""
    items = list(state.get("evidence_items", ()))[:limit]
    return "\n".join(
        f"[{str(item.source)[:100]}] {str(item.observation)[:200]}"
        for item in items
    )[:3000]
