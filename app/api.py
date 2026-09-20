"""FastAPI interface for SentinelOps investigations."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.schemas import (
    AdjudicationResponse,
    ApprovalRequest,
    EvidenceResponse,
    HypothesisResponse,
    InvestigationResponse,
    RecoveryPlanResponse,
    SafetyDecisionResponse,
)
from graph.investigation import build_investigation_graph
from memory.checkpoint import create_checkpointer
from simulator.scenarios import build_benchmark_evidence


app = FastAPI(
    title="SentinelOps API",
    version="0.1.0",
    description="API for evidence-backed incident investigation and safe recovery planning.",
)

_DASHBOARD_PATH = Path(__file__).parent / "static" / "index.html"
_CHECKPOINTER = create_checkpointer()
_GRAPH = build_investigation_graph(
    checkpointer=_CHECKPOINTER,
    incident_memory_repository=None,
)


class InvestigationRequest(BaseModel):
    """Request to investigate one deterministic SentinelOps benchmark incident."""

    incident_id: str = Field(
        min_length=1,
        description="Benchmark incident identifier, e.g. INC-002",
    )


def _jsonable(value: Any) -> Any:
    """Convert SentinelOps dataclasses and nested tuples into JSON-safe data."""
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value.isoformat() if hasattr(value, "isoformat") else value


def _investigation_response(state: dict[str, Any]) -> InvestigationResponse:
    """Map internal LangGraph state into the stable public API contract."""
    return InvestigationResponse(
        incident_id=state["incident_id"],
        status=state.get("investigation_status", "unknown"),
        approval_status=state.get("approval_status", "not_required"),
        approval_required=bool(state.get("approval_required", False)),
        root_cause=(
            AdjudicationResponse.model_validate(_jsonable(state["adjudication"]))
            if state.get("adjudication") is not None
            else None
        ),
        hypotheses=[
            HypothesisResponse.model_validate(_jsonable(hypothesis))
            for hypothesis in state.get("hypotheses", [])
        ],
        evidence=[
            EvidenceResponse.model_validate(_jsonable(item))
            for item in state.get("evidence_items", [])
        ],
        recovery_plan=(
            RecoveryPlanResponse.model_validate(_jsonable(state["recovery_plan"]))
            if state.get("recovery_plan") is not None
            else None
        ),
        safety_decision=(
            SafetyDecisionResponse.model_validate(_jsonable(state["safety_decision"]))
            if state.get("safety_decision") is not None
            else None
        ),
        messages=list(state.get("messages", [])),
    )


def _config(incident_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": incident_id}}


@app.get("/health")
def health() -> dict[str, str]:
    """Return API liveness information."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the lightweight SentinelOps investigation dashboard."""
    return FileResponse(_DASHBOARD_PATH, media_type="text/html")


@app.post("/api/v1/investigations", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    """Start an investigation and stop at the human approval checkpoint when required."""
    try:
        evidence = build_benchmark_evidence(request.incident_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown incident_id: {request.incident_id}",
        ) from exc

    initial_state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }
    state = _GRAPH.invoke(initial_state, config=_config(request.incident_id))
    return _investigation_response(state)


@app.post(
    "/api/v1/investigations/{incident_id}/approval",
    response_model=InvestigationResponse,
)
def approve_investigation(
    incident_id: str,
    request: ApprovalRequest,
) -> InvestigationResponse:
    """Resume a pending investigation with an explicit human approval decision."""
    try:
        _ = build_benchmark_evidence(incident_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown incident_id: {incident_id}",
        ) from exc

    config = _config(incident_id)
    snapshot = _GRAPH.get_state(config)
    values = snapshot.values

    if not values:
        raise HTTPException(
            status_code=404,
            detail=f"No investigation checkpoint found for: {incident_id}",
        )

    if values.get("investigation_status") != "awaiting_human_approval":
        raise HTTPException(
            status_code=409,
            detail="Investigation is not awaiting human approval.",
        )

    if not values.get("approval_required"):
        raise HTTPException(
            status_code=409,
            detail="Investigation no longer requires human approval.",
        )

    state = _GRAPH.invoke(
        Command(resume={"approved": request.approved, "reviewer": request.reviewer}),
        config=config,
    )
    return _investigation_response(state)
