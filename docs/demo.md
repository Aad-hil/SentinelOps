# SentinelOps Redshift Demo Guide

## Goal

Demonstrate an evidence-led Amazon Redshift incident investigation, from synthetic AWS-style evidence through human-reviewed recovery planning. No production changes are executed.

## Start locally

```powershell
.\.venv\Scripts\Activate.ps1
$env:SENTINELOPS_CHECKPOINT_BACKEND="memory"
python -m uvicorn app.api:app --reload
```

Open http://127.0.0.1:8000/ and select one of the RS-001 through RS-012 scenarios.

## Suggested walkthrough

1. **Incident context:** show the Redshift workload, incident severity, and synthetic-data label.
2. **Evidence:** inspect the relevant Redshift query/WLM/load/cluster signals and related AWS dependency evidence.
3. **Candidate hypotheses:** explain the RSH1-RSH12 taxonomy. Candidates are ranked by evidence; confidence is not a calibrated probability.
4. **Adjudication:** show the leading hypothesis, causal/temporal support, contradictions, and evidence gaps.
5. **Recovery plan:** inspect Redshift-specific diagnostic and proposed remediation steps.
6. **Safety and human approval:** explain that disruptive changes require review and are not executed by SentinelOps.
7. **Agent timeline:** show the recorded execution events for the LangGraph workflow.

RS-012 is the unknown/compound case. Use it to demonstrate that SentinelOps can request more diagnostics instead of forcing a specific root cause.

## API

- `GET /health`
- `GET /api/v1/incidents`
- `POST /api/v1/investigations` with `{"incident_id":"RS-001"}`
- `POST /api/v1/investigations/RS-001/approval` with `{"approved":true,"reviewer":"Demo Reviewer"}`
- Swagger: http://127.0.0.1:8000/docs

## Evaluation

Run the Redshift hypothesis benchmark:

```powershell
python -m evaluation.redshift_runner
```

It evaluates 12 deterministic synthetic scenarios. The benchmark label is read only after candidate generation and is never passed into the agent state. This measures the hypothesis-ranking component, not end-to-end production RCA accuracy.

## Interview explanation

> SentinelOps is a LangGraph-based multi-agent incident investigation and safe recovery planning system focused exclusively on Amazon Redshift workloads. Specialized agents collect and interpret synthetic telemetry, retrieve operational knowledge, inspect change context, rank RSH1-RSH12 hypotheses, critique and adjudicate evidence, and prepare a Redshift-aware recovery plan. Safety controls and a human approval checkpoint keep potentially disruptive actions as proposals rather than autonomous production changes.
