# Local LLM mode (Ollama)

SentinelOps supports optional, read-only LLM explanations for the Root Cause and Critic agents, plus a grounded RCA Copilot. The underlying hypothesis ranking, adjudication, safety policy, and human approval remain deterministic.

## Windows quick start

Install Ollama, then:

```powershell
ollama pull qwen3:4b
cd C:\Users\aadhi\PycharmProjects\sentinelops
$env:SENTINELOPS_CHECKPOINT_BACKEND="memory"
$env:SENTINELOPS_RAG_ENABLED="false"
$env:SENTINELOPS_LLM_ENABLED="true"
$env:SENTINELOPS_LLM_MODEL="qwen3:4b"
$env:SENTINELOPS_LLM_TIMEOUT="45"
python -m uvicorn app.api:app --reload
```

Open http://127.0.0.1:8000 and investigate a new incident. Open Agent Studio to inspect findings, and RCA Copilot to ask questions. The Copilot endpoint is `POST /api/v1/incidents/{incident_id}/copilot` with JSON `{"question":"Why was this incident blocked?"}`.

The Ollama client uses `think: false`, `stream: false`, `temperature: 0`, a bounded context and output limit. Ollama must be listening on localhost:11434. If unavailable, the optional LLM findings are skipped and Copilot reports unavailability. CPU inference on a 16 GB integrated-graphics laptop can be slow; adjust `SENTINELOPS_LLM_TIMEOUT` if needed.

**Important:** LLM explanations are commentary only, not validated factual claims. Do not treat them as evidence or use them to authorize production changes. This is a synthetic local demo, not a live Redshift integration. To turn the feature off, set `SENTINELOPS_LLM_ENABLED=false`.

Run tests with `python -m pytest tests/ -v`. This integration has not yet been locally end-to-end tested.
