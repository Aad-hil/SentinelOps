[![CI](https://github.com/Aad-hil/SentinelOps/actions/workflows/ci.yml/badge.svg)](https://github.com/Aad-hil/SentinelOps/actions/workflows/ci.yml)

# SentinelOps

**SentinelOps** is an evidence-backed, multi-agent incident investigation and safe recovery planning platform.

It simulates production incidents and coordinates specialized agents to collect telemetry, retrieve relevant knowledge and historical incidents, inspect deployment context, generate competing root-cause hypotheses, critique them, adjudicate the evidence, build a recovery plan, and enforce a human approval checkpoint before any production-changing action could proceed.

> **Safety boundary:** SentinelOps does **not** execute remediation actions against production systems. Recovery steps are proposed for review, and potentially impactful steps require explicit human approval.

## Project status

**Phase 7 — API, dashboard, durable state, HITL, observability, and evaluation complete.**

Current investigation flow:

`Historical Memory → Supervisor → Telemetry → Knowledge → Deployment → Root Cause → Critic → Adjudication → Recovery → Safety → Human Approval`

The dashboard exposes the investigation result, evidence, competing hypotheses, recovery plan, safety decision, and a structured agent execution timeline.

## What SentinelOps demonstrates

- **True multi-agent orchestration** — specialized agents have separate responsibilities and tools.
- **RAG** — knowledge and historical incident retrieval feed the investigation.
- **Evidence-backed RCA** — hypotheses are supported by normalized evidence and causal relationships.
- **Competing hypotheses** — the system does not immediately collapse to one explanation.
- **Critique and adjudication** — candidate explanations are challenged and evaluated against temporal/causal evidence.
- **Recovery planning** — remediation is proposed as structured, evidence-aware steps.
- **Safety controls** — risk and approval requirements are evaluated before recovery.
- **Human-in-the-loop** — investigations can pause at a durable approval checkpoint.
- **Durable state** — PostgreSQL-backed LangGraph checkpoints persist investigation state across API restarts.
- **Observability** — OpenTelemetry traces plus a local execution timeline expose agent/node execution.
- **Deterministic evaluation** — a 15-incident synthetic benchmark measures hypothesis, evidence, RCA, and recovery performance.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture and Mermaid diagram.

At a high level:

```text
                         ┌──────────────────────┐
                         │   FastAPI + Dashboard │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  LangGraph Supervisor│
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
        Telemetry Agent       Knowledge/RAG Agent    Deployment Agent
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                           Root Cause Agent
                                    │
                                    ▼
                              Critic Agent
                                    │
                                    ▼
                           Adjudication Layer
                                    │
                                    ▼
                           Recovery Planner
                                    │
                                    ▼
                              Safety Agent
                                    │
                                    ▼
                         Human Approval Checkpoint
```

Supporting infrastructure includes PostgreSQL for durable state and incident memory, Qdrant for semantic retrieval, and OpenTelemetry/Jaeger for tracing.

## Agents and responsibilities

| Component | Responsibility |
|---|---|
| Historical Memory | Retrieves relevant prior incident context. |
| Supervisor | Plans and coordinates the investigation sequence. |
| Telemetry Agent | Examines metrics, traces, logs, and operational signals. |
| Knowledge Agent | Retrieves relevant documentation/knowledge through RAG. |
| Deployment Agent | Correlates deployment/change history with incident timing. |
| Root Cause Agent | Generates and scores competing hypotheses using evidence and causal relationships. |
| Critic Agent | Challenges the leading explanation and identifies gaps/contradictions. |
| Adjudication | Consolidates temporal and causal support into the selected hypothesis. |
| Recovery Planner | Produces structured, evidence-aware remediation steps. |
| Safety Agent | Evaluates risk and determines whether human approval is required. |
| Human Approval | Explicitly approves or blocks the proposed recovery path. |

## Technology stack

- **Python 3.13**
- **FastAPI**
- **LangGraph**
- **PostgreSQL**
- **Qdrant**
- **OpenTelemetry**
- **Jaeger**
- **pytest**
- **Docker Compose** for supporting local observability services
- AWS Bedrock embeddings where configured
- OpenAI API where configured for generation
- Optional LangSmith tracing

The default development path is designed to avoid paid infrastructure. External model/API usage can incur provider charges when enabled.

## Local setup

### 1. Clone the repository

```powershell
git clone https://github.com/Aad-hil/SentinelOps.git
cd SentinelOps
```

### 2. Create and activate a Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install the project

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest pytest-cov ruff
```

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Fill in the values required by the features you intend to run.

For isolated tests and the deterministic benchmark, use:

```env
SENTINELOPS_CHECKPOINT_BACKEND=memory
```

For the API's normal durable state, PostgreSQL is the default:

```env
SENTINELOPS_CHECKPOINT_BACKEND=postgres
```

See [.env.example](.env.example) for PostgreSQL, Qdrant, AWS Bedrock, OpenAI, LangSmith, and OpenTelemetry settings.

## Run the API and dashboard

```powershell
python -m uvicorn app.api:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs

The dashboard starts with a benchmark incident and lets you investigate another incident ID directly.

## Human approval flow

Some investigations stop at:

```text
awaiting_human_approval
```

The dashboard presents the proposed recovery plan and reviewer controls.

The approval endpoint is:

```text
POST /api/v1/investigations/{incident_id}/approval
```

with:

```json
{
  "approved": true,
  "reviewer": "reviewer-name"
}
```

Approval does not execute infrastructure changes. It records the human decision and lets the investigation graph reach its terminal state.

## Observability

SentinelOps records structured execution events for graph nodes, including:

- trace ID
- incident ID
- node/agent name
- status
- timestamp
- execution duration
- state keys produced
- error information when applicable

The dashboard displays these events as an **Agent Execution Timeline**.

For local Jaeger tracing, the repository includes:

```powershell
docker compose -f docker-compose.observability.yml up -d
```

Then open Jaeger at:

http://127.0.0.1:16686

Set the OTLP endpoint in `.env` when exporting SentinelOps spans to the local collector:

```env
SENTINELOPS_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Evaluation

SentinelOps includes 15 deterministic incident scenarios with expected root causes, evidence concepts, and recovery concepts.

Latest benchmark snapshot:

| Metric | Result |
|---|---:|
| Incidents | 15 / 15 |
| Top-1 hypothesis accuracy | 100% |
| Top-3 hypothesis recall | 100% |
| Mean root-cause concept match | 85.0% |
| Mean evidence coverage | 97.0% |
| Mean recovery match | 84.4% |
| Mean investigation duration | ~29 ms |

Run the benchmark with:

```powershell
python -m evaluation.runner
```

Run the automated test suite with:

```powershell
pytest
```

The benchmark is deterministic and uses synthetic incident evidence. It is intended to measure SentinelOps' reasoning pipeline, not to claim production incident-resolution accuracy.

## Benchmark provenance

The benchmark contains controlled synthetic scenarios. Several scenarios are synthetic reconstructions of facts described in public GitHub availability reports; the repository explicitly labels their provenance and does not include private GitHub telemetry.

See [evaluation/incident_cases.json](evaluation/incident_cases.json) for the complete case definitions, expected hypotheses, required evidence, mitigations, and source notes.

## Durable checkpointing

PostgreSQL-backed LangGraph checkpoints are enabled by default for the API. The incident ID is used as the LangGraph `thread_id`, allowing an interrupted investigation to be resumed after an API process restart when the same PostgreSQL checkpoint store is available.

The checkpointer creates its own LangGraph checkpoint tables through `PostgresSaver.setup()`; no application-specific migration file is required for those tables.

For isolated tests/experiments, switch to:

```env
SENTINELOPS_CHECKPOINT_BACKEND=memory
```

## Optional LangSmith

LangSmith is optional and disabled by default.

```env
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=sentinelops
```

The default observability path remains local OpenTelemetry + Jaeger so external observability accounts are not required.

## Repository structure

```text
sentinelops/
├── agents/             # Specialized investigation agents
├── app/                # FastAPI API, schemas, and dashboard
├── evaluation/         # Benchmark cases, metrics, and runner
├── graph/              # LangGraph state and investigation graph
├── memory/             # Historical memory and durable checkpoints
├── observability/      # OpenTelemetry configuration/tracing
├── rag/                # Retrieval and knowledge pipeline
├── recovery/           # Recovery plan generation
├── safety/              # Safety policy and human approval
├── simulator/          # Deterministic incident/evidence simulator
├── tests/              # Automated tests
├── docs/               # Architecture and demo documentation
├── .env.example
├── pyproject.toml
└── README.md
```

## Demo path

A concise portfolio demo is documented in [docs/demo.md](docs/demo.md).

Recommended flow:

1. Start the API.
2. Investigate `INC-002`.
3. Show the evidence and competing hypotheses.
4. Show the adjudicated root cause.
5. Show the structured recovery plan.
6. Show the safety decision and approval checkpoint.
7. Show the Agent Execution Timeline.
8. Demonstrate approve/reject through the HITL endpoint.

## Project status and limitations

SentinelOps is a portfolio/research project built around deterministic simulated incidents.

It is **not** a production incident-management system and does not automatically modify production infrastructure.

Known limitations include:

- benchmark evidence is simulated;
- model/provider integrations can be configured but the deterministic benchmark is designed to run locally;
- recovery matching is concept-based rather than a production safety certification;
- observability is intentionally lightweight;
- the project does not claim that benchmark accuracy transfers directly to real-world incidents.

## License

TBD
