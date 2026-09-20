# SentinelOps

SentinelOps is an AI-powered incident investigation and response platform.

The system investigates simulated production incidents using telemetry, documentation, deployment history, and previous incidents to identify likely root causes and produce evidence-backed remediation plans.

## Project Status

🚧 Phase 7 — API, Dashboard & Durable Investigation State

Current end-to-end flow:

`Historical Memory → Supervisor → Telemetry/Knowledge/Deployment → Root Cause → Critic → Adjudication → Recovery → Safety → Human Approval Checkpoint`

The system can investigate synthetic incidents, retrieve historical context, produce competing root-cause hypotheses, build evidence-aware recovery plans, and stop for explicit human approval before production-changing actions. Recovery actions are not executed automatically.

## Core Goals

- Multi-agent incident investigation
- Retrieval-Augmented Generation (RAG)
- Evidence-backed root-cause analysis
- Competing hypotheses and critique
- Safe remediation planning
- Deterministic safety policy and risk review
- Human-in-the-loop approval checkpoint
- Agent observability
- Automated evaluation

## Architecture

Coming soon.

## Development

- Python 3.13
- Docker Compose
- FastAPI
- LangGraph
- PostgreSQL
- Qdrant
- PostgreSQL-backed LangGraph checkpoints

## Durable Checkpointing

SentinelOps uses PostgreSQL-backed LangGraph checkpoints by default. This keeps investigation state and human-approval interruptions available across API process restarts, using the incident ID as the LangGraph `thread_id`.

Install the checkpoint dependencies with:

```powershell
uv sync
```

Configure the PostgreSQL settings in `.env` from `.env.example`, then start the database used by your local environment.

For isolated tests or experiments, set:

```env
SENTINELOPS_CHECKPOINT_BACKEND=memory
```

The PostgreSQL checkpointer creates and migrates its own checkpoint tables through `PostgresSaver.setup()`. No application-specific migration file is required for those tables.

## License

TBD

## Optional LangSmith Tracing

SentinelOps already has local OpenTelemetry tracing with Jaeger. LangSmith is an **optional secondary backend** for agent-focused debugging and evaluation.

Leave these disabled unless you intentionally want to send traces to LangSmith:

```env
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=sentinelops
```

When enabled, LangGraph/LangChain tracing can be collected by LangSmith using the environment configuration. This is intentionally opt-in so the default development workflow remains local and does not require an external observability account.

OpenTelemetry + local Jaeger remains the primary zero-cost observability path for SentinelOps.
