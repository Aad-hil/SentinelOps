"""FastAPI interface for SentinelOps investigations."""

from __future__ import annotations

import os
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
from rag.retrieval import create_knowledge_retriever_from_env
from simulator.scenarios import build_benchmark_evidence
from simulator.benchmark import benchmark_category, build_all_benchmark_incidents


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
_KNOWLEDGE_RETRIEVER: Any | None = None
_RETRIEVER_INITIALIZED = False


class InvestigationRequest(BaseModel):
    """Request to investigate one deterministic SentinelOps benchmark incident."""

    incident_id: str = Field(
        min_length=1,
        description="Benchmark incident identifier, e.g. INC-002",
    )


def _get_knowledge_retriever() -> Any | None:
    """Load RAG only when explicitly enabled; local demo mode has no cloud dependency."""
    global _KNOWLEDGE_RETRIEVER, _RETRIEVER_INITIALIZED
    if os.getenv("SENTINELOPS_RAG_ENABLED", "false").strip().lower() != "true":
        return None
    if not _RETRIEVER_INITIALIZED:
        try:
            _KNOWLEDGE_RETRIEVER = create_knowledge_retriever_from_env()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "RAG is enabled but its embedding/vector-store dependencies "
                    f"could not be initialized: {exc}"
                ),
            ) from exc
        _RETRIEVER_INITIALIZED = True
    return _KNOWLEDGE_RETRIEVER


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
            if hypothesis is not None
        ],
        evidence=[
            EvidenceResponse.model_validate(_jsonable(item))
            for item in state.get("evidence_items", [])
            if item is not None
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
        observability_events=[
            {
                **event,
                "trace_id": event.get("trace_id", ""),
                "output_keys": list(event.get("output_keys", [])),
            }
            for event in state.get("observability_events", [])
        ],
        trace_id=state.get("otel_trace_id"),
    )


def _config(
    incident_id: str,
    *,
    knowledge_retriever: Any | None = None,
) -> dict[str, Any]:
    configurable: dict[str, Any] = {"thread_id": incident_id}
    if knowledge_retriever is not None:
        configurable["knowledge_retriever"] = knowledge_retriever
    return {"configurable": configurable}


@app.get("/health")
def health() -> dict[str, str]:
    """Return API liveness information."""
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the lightweight SentinelOps investigation dashboard."""
    return FileResponse(_DASHBOARD_PATH, media_type="text/html")


@app.get("/api/v1/incidents")
def list_incidents() -> list[dict[str, Any]]:
    """List benchmark incidents with their persisted investigation status."""
    incidents = build_all_benchmark_incidents()
    results = []
    for scenario in incidents:
        snapshot = _GRAPH.get_state(_config(scenario.incident.incident_id))
        values = snapshot.values or {}
        results.append({
            "incident_id": scenario.incident.incident_id,
            "category": benchmark_category(scenario.incident.incident_id),
            "title": scenario.incident.title,
            "service": scenario.incident.service,
            "severity": scenario.incident.severity,
            "description": scenario.incident.description,
            "status": values.get("investigation_status", "not_started"),
            "approval_status": values.get("approval_status", "not_started"),
            "approval_required": bool(values.get("approval_required", False)),
            "has_investigation": bool(values),
        })
    return results


@app.get("/api/v1/incidents/{incident_id}", response_model=InvestigationResponse)
def get_incident(incident_id: str) -> InvestigationResponse:
    """Return the saved investigation for one incident without running agents."""
    try:
        build_benchmark_evidence(incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown incident_id: {incident_id}") from exc
    snapshot = _GRAPH.get_state(_config(incident_id))
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No investigation found for: {incident_id}")
    return _investigation_response(snapshot.values)


@app.delete("/api/v1/incidents/{incident_id}")
def delete_incident(incident_id: str) -> dict[str, str]:
    """Delete one incident's saved investigation checkpoint."""
    try:
        build_benchmark_evidence(incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown incident_id: {incident_id}") from exc
    snapshot = _GRAPH.get_state(_config(incident_id))
    if not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No saved investigation for: {incident_id}")
    _CHECKPOINTER.delete_thread(incident_id)
    return {"incident_id": incident_id, "status": "deleted"}


@app.post("/api/v1/investigations", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    """Start only if no saved investigation exists; otherwise return its current result."""
    try:
        evidence = build_benchmark_evidence(request.incident_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown incident_id: {request.incident_id}",
        ) from exc

    config = _config(request.incident_id)
    previous = _GRAPH.get_state(config)
    if previous.values:
        previous_values = previous.values
        is_pending_approval = (
            previous_values.get("investigation_status") == "awaiting_human_approval"
            and previous_values.get("approval_required") is True
            and previous_values.get("approval_status") == "pending"
        )
        has_real_approval_interrupt = any(
            task.name == "human_approval" and bool(task.interrupts)
            for task in previous.tasks
        )

        if is_pending_approval and has_real_approval_interrupt:
            raise HTTPException(
                status_code=409,
                detail="Investigation is waiting for human approval.",
            )

        if is_pending_approval:
            # A stale/incomplete checkpoint can claim approval is pending
            # without ever reaching the human_approval interrupt. Discard it
            # and start a clean investigation for this incident.
            _CHECKPOINTER.delete_thread(request.incident_id)
        else:
            # Completed, blocked, or already-approved investigations are
            # reopened from their saved result rather than executed again.
            return _investigation_response(previous_values)

    initial_state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }
    retriever = _get_knowledge_retriever()
    state = _GRAPH.invoke(
        initial_state,
        config=_config(request.incident_id, knowledge_retriever=retriever),
    )
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
