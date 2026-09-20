"""FastAPI interface for SentinelOps investigations."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.schemas import (
    AdjudicationResponse,
    EvidenceResponse,
    HypothesisResponse,
    InvestigationResponse,
    RecoveryPlanResponse,
    SafetyDecisionResponse,
)
from graph.investigation import build_investigation_graph
from simulator.scenarios import build_benchmark_evidence


app = FastAPI(
    title="SentinelOps API",
    version="0.1.0",
    description="API for evidence-backed incident investigation and safe recovery planning.",
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


@app.get("/health")
def health() -> dict[str, str]:
    """Return API liveness information."""
    return {"status": "ok"}


@app.post("/api/v1/investigations", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    """Run an investigation against a deterministic benchmark incident."""
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
    graph = build_investigation_graph(
        checkpointer=None,
        incident_memory_repository=None,
    )
    state = graph.invoke(initial_state)
    return _investigation_response(state)
