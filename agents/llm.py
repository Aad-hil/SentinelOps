"""Optional local Ollama reasoning; never used to authorize remediation.

The model may explain evidence but cannot modify scored hypotheses, evidence,
adjudication, safety decisions, or approval state.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def enabled() -> bool:
    return os.getenv("SENTINELOPS_LLM_ENABLED", "false").lower() in ("1", "true", "yes")


def ask(system: str, user: str, *, max_tokens: int = 300) -> str | None:
    """Return model text or None; failures preserve deterministic execution."""
    if not enabled():
        return None
    host = os.getenv("SENTINELOPS_OLLAMA_URL", "http://localhost:11434").rstrip("/")
    # Never send evidence to an arbitrary remote endpoint by default.
    if not (host.startswith("http://localhost:") or host.startswith("http://127.0.0.1:")):
        return None
    payload = {
        "model": os.getenv("SENTINELOPS_LLM_MODEL", "qwen3:4b"),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": max_tokens, "num_ctx": 2048},
    }
    request = Request(
        host + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=float(os.getenv("SENTINELOPS_LLM_TIMEOUT", "45"))) as response:
            data = json.load(response)
        text = data.get("message", {}).get("content", "")
        return text.strip()[:2400] or None
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, KeyError):
        return None


def evidence_context(state, *, limit: int = 18) -> str:
    """Only pass bounded observed evidence, not hidden ground-truth labels."""
    items = list(state.get("evidence_items", ()))[:limit]
    return "\n".join(
        f"[{str(item.source)[:100]}] {str(item.observation)[:350]}"
        for item in items
    )[:5500]
