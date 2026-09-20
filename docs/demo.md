# SentinelOps Demo Guide

## Goal

Demonstrate one complete incident investigation from evidence collection through human approval without executing any production-changing action.

## Start

Activate the virtual environment and start the API:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.api:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

## Suggested demo: INC-002

Use `INC-002`, the primary database saturation scenario.

Walk through the dashboard in this order:

### 1. Incident

Show the incident ID and investigation status.

### 2. Evidence

Point out the deployment/change evidence, database saturation signals, and service impact evidence.

### 3. Competing hypotheses

Open several hypotheses and show that the system retains alternatives instead of presenting only one unexplained answer.

### 4. Root cause

Show:

- hypothesis ID;
- confidence;
- rationale;
- temporal support;
- causal support;
- recovery support.

### 5. Recovery plan

Show the structured recovery steps and their risk/approval metadata.

Emphasize that these are **proposals**, not executed actions.

### 6. Safety decision

Show whether the safety layer requires human approval.

### 7. Execution timeline

Scroll through the Agent Execution Timeline.

Point out that the graph records separate execution events for the historical memory, supervisor, telemetry, knowledge, deployment, root-cause, critic, adjudication, recovery, and safety stages.

### 8. Human approval

For an investigation awaiting approval, enter a reviewer name and approve or reject the proposed recovery.

The approval request is sent to:

```text
POST /api/v1/investigations/{incident_id}/approval
```

No infrastructure action is executed by this endpoint.

## Interview explanation

A concise explanation of the architecture:

> SentinelOps is a LangGraph-based multi-agent incident investigation system. A supervisor coordinates specialized agents for telemetry, knowledge retrieval, deployment analysis, root-cause generation, critique, adjudication, recovery planning, and safety. Evidence and causal relationships are kept in shared state, while PostgreSQL checkpoints make human approval interruptions durable. The dashboard exposes the investigation and OpenTelemetry execution timeline, and a deterministic 15-incident benchmark evaluates hypothesis accuracy, evidence coverage, RCA concepts, and recovery matching.

## Useful API endpoints

### Health

```http
GET /health
```

### Start investigation

```http
POST /api/v1/investigations
Content-Type: application/json

{"incident_id":"INC-002"}
```

### Human approval

```http
POST /api/v1/investigations/INC-002/approval
Content-Type: application/json

{"approved":true,"reviewer":"Demo Reviewer"}
```

### Swagger

```text
http://127.0.0.1:8000/docs
```
