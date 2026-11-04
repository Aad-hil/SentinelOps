"""Optional evidence-grounded inference via Groq or local Ollama.

LLM text is advisory; deterministic scoring, safety and approval remain authoritative.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def provider() -> str:
    return os.getenv("SENTINELOPS_LLM_PROVIDER", "ollama").strip().lower()


def enabled() -> bool:
    return os.getenv("SENTINELOPS_LLM_ENABLED", "false").strip().lower() in ("1", "true", "yes")


def ask(system: str, user: str, *, max_tokens: int = 300) -> str | None:
    """Return advisory model text; return None on missing credentials or API errors."""
    if not enabled():
        return None
    model_provider = provider()
    limit = max(1, min(max_tokens, int(os.getenv("SENTINELOPS_LLM_MAX_TOKENS", "160"))))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if model_provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + api_key}
        payload = {
            "model": os.getenv("SENTINELOPS_LLM_MODEL", "llama-3.3-70b-versatile"),
            "messages": messages,
            "stream": False,
            "temperature": 0,
            "max_completion_tokens": limit,
        }
    elif model_provider == "ollama":
        host = os.getenv("SENTINELOPS_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        if not (host.startswith("http://localhost:") or host.startswith("http://127.0.0.1:")):
            return None
        url = host + "/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": os.getenv("SENTINELOPS_LLM_MODEL", "qwen3:4b"),
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": limit,
                        "num_ctx": int(os.getenv("SENTINELOPS_LLM_CONTEXT", "1536"))},
        }
    else:
        return None

    request = Request(url, data=json.dumps(payload).encode("utf-8"),
                      headers=headers, method="POST")
    try:
        with urlopen(request, timeout=float(os.getenv("SENTINELOPS_LLM_TIMEOUT", "45"))) as response:
            data = json.load(response)
        if model_provider == "groq":
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            text = data.get("message", {}).get("content", "")
        return text.strip()[:2400] or None if isinstance(text, str) else None
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, KeyError, IndexError):
        return None


def evidence_context(state, *, limit: int = 10) -> str:
    """Only pass bounded observed evidence, not hidden ground-truth labels."""
    items = list(state.get("evidence_items", ()))[:limit]
    return "\n".join(
        f"[{str(item.source)[:100]}] {str(item.observation)[:200]}"
        for item in items
    )[:3000]
