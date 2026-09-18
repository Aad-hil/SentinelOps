# SentinelOps

SentinelOps is an AI-powered incident investigation and response platform.

The system investigates simulated production incidents using telemetry, documentation, deployment history, and previous incidents to identify likely root causes and produce evidence-backed remediation plans.

## Project Status

🚧 Phase 4 — Investigation, Memory & Safe Recovery

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

## License

TBD
