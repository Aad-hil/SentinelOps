# SentinelOps in GitHub Codespaces with Groq

This mode runs FastAPI and LangGraph in Codespaces and sends only the synthetic incident evidence included in LLM prompts to Groq. No local Ollama is required. Deterministic scoring, safety decisions and human approval remain unchanged.

## 1. Create a Groq API key

Create a key at https://console.groq.com/keys. Do **not** paste it into chat, commit it to Git, or include it in .env.example.

In GitHub, open **Settings → Codespaces → Secrets → New secret**, create `GROQ_API_KEY`, and grant it access to the SentinelOps repository. Restart the Codespace if the secret was added after creation.

For a single Codespace, alternatively set the key as a private environment variable in the terminal. Do not store it in tracked files.

## 2. Configure Codespaces

Create/update the ignored local `.env` file:

```dotenv
APP_ENV=development
SENTINELOPS_CHECKPOINT_BACKEND=memory
SENTINELOPS_RAG_ENABLED=false
SENTINELOPS_LLM_ENABLED=true
SENTINELOPS_LLM_PROVIDER=groq
SENTINELOPS_LLM_MODEL=llama-3.3-70b-versatile
SENTINELOPS_LLM_MAX_TOKENS=160
SENTINELOPS_LLM_TIMEOUT=45
```

The application loads `.env` automatically, but pre-existing environment variables (including Codespaces secrets) take precedence. Verify the model is available to your Groq account and change the model ID if needed. Free-tier quotas and supported models can change.

## 3. Run

```bash
python -m uvicorn app.api:app --host 0.0.0.0 --port 8000
```

Open the forwarded port 8000 (prefer **Private** visibility). Investigate an unsaved synthetic incident to see live agent completion events and Groq-generated Root Cause and Critic explanations. Saved incidents are not automatically reprocessed; delete a saved investigation before rerunning.

RCA Copilot uses the same selected provider. A missing key, quota error or timeout returns an unavailable response rather than changing the deterministic outcome.

## 4. Local Ollama fallback

Set `SENTINELOPS_LLM_PROVIDER=ollama`, `SENTINELOPS_LLM_MODEL=qwen3:4b` and `SENTINELOPS_OLLAMA_URL=http://localhost:11434` in a local environment.

The live investigation stream reports **node completions and finished LLM findings**, not individual generated tokens.
