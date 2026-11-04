[![CI](https://github.com/Aad-hil/SentinelOps/actions/workflows/ci.yml/badge.svg)](https://github.com/Aad-hil/SentinelOps/actions/workflows/ci.yml)

# SentinelOps

**SentinelOps** is a Redshift-focused, evidence-led multi-agent incident investigation and safe recovery planning system.

It coordinates specialized agents to inspect operational evidence, retrieve relevant runbooks, rank competing Redshift failure hypotheses, critique and adjudicate the evidence, and prepare recovery proposals with safety checks and a human approval checkpoint.

> **Safety boundary:** SentinelOps does not execute production remediation. Potentially disruptive actions remain proposals for operator review.

## Scope: Amazon Redshift only

Amazon Redshift is the only supported incident domain. Direct dependencies are considered only when they affect a Redshift workload: Amazon S3, AWS Glue Data Catalog, IAM, KMS, VPC, and CloudWatch.

The active taxonomy contains twelve Redshift hypotheses:

| ID | Failure mode |
|---|---|
| RSH1 | WLM queue contention / workload concurrency |
| RSH2 | Inefficient SQL / query-plan regression |
| RSH3 | Compute capacity / cluster sizing pressure |
| RSH4 | COPY / UNLOAD data-loading bottleneck |
| RSH5 | Redshift Spectrum / external-data dependency |
| RSH6 | Table design, data skew, statistics, or maintenance |
| RSH7 | Storage pressure / query spill |
| RSH8 | IAM, KMS, or authorization failure |
| RSH9 | VPC connectivity / client connection path |
| RSH10 | Cluster health, maintenance, or infrastructure event |
| RSH11 | Data sharing producer/consumer issue |
| RSH12 | Unknown or compound Redshift failure |

RSH12 is an intentional fallback. SentinelOps should report insufficient evidence rather than force a diagnosis. Confidence is a heuristic ranking score, not a calibrated probability.

## Investigation flow

`Historical Memory → Supervisor ↔ Telemetry / Knowledge / Deployment / Root Cause / Critic / Adjudication / Recovery / Safety → Supervisor LLM Summary → Human Approval`

LangGraph coordinates the workflow and shared investigation state. Checkpointing supports resumable investigations and approval interrupts. The dashboard displays incident evidence, ranked hypotheses, recovery proposals, safety decisions, and recorded agent execution events.

## Run locally

Python 3.13 is required by `pyproject.toml`. Create and activate a virtual environment, install the project dependencies, then:

```powershell
Copy-Item .env.example .env
$env:SENTINELOPS_CHECKPOINT_BACKEND="memory"
python -m uvicorn app.api:app --reload
```

Open the dashboard at http://127.0.0.1:8000/ and API docs at http://127.0.0.1:8000/docs.

To enable LLM analysis, set `SENTINELOPS_LLM_ENABLED=true` and `GROQ_API_KEY` in `.env`. The Recovery Agent generates a short LLM advisory by default when LLMs are enabled; its structured plan remains deterministic so the Safety Agent can enforce fixed policies. Set `SENTINELOPS_RECOVERY_LLM_ENABLED=false` to skip that extra call. The local deterministic simulator and benchmark do not require an AWS account. All generated evidence is synthetic and must not be represented as live AWS telemetry.

## Investigate an incident

```http
POST /api/v1/investigations
Content-Type: application/json

{"incident_id":"RS-001"}
```

List available cases with `GET /api/v1/incidents`. The simulator provides RS-001 through RS-012.

For an investigation awaiting review:

```http
POST /api/v1/investigations/RS-001/approval
Content-Type: application/json

{"approved":true,"reviewer":"Demo Reviewer"}
```

Approval records the human decision; it does not execute AWS changes.

## Evaluate

```powershell
python -m evaluation.redshift_runner
```

The evaluator runs 12 deterministic Redshift scenarios and compares the ranked hypothesis with simulator labels only after candidate generation. It evaluates the hypothesis-ranking component, not end-to-end real-world diagnostic accuracy.

Run tests with:

```powershell
pytest
```

## Architecture and demo

- [Redshift domain scope](docs/redshift-domain.md)
- [Redshift demo guide](docs/demo.md)

## Limitations

- Scenarios and evidence are synthetic.
- No live Redshift/AWS telemetry is collected by the default local demo.
- Benchmark results do not establish production accuracy.
- Recovery steps are recommendations; production changes are not autonomously executed.
- The RSH1-RSH12 taxonomy is a candidate set, not an exhaustive representation of every possible Redshift failure.
