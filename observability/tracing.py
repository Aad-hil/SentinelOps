from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from graph.state import InvestigationState


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_trace(
    state: InvestigationState,
    *,
    trace_id: str,
    node: str,
    status: str,
    duration_ms: float,
    output_keys: tuple[str, ...] = (),
    error: str | None = None,
) -> list[dict[str, Any]]:
    events = list(state.get("observability_events", []))
    event: dict[str, Any] = {
        "trace_id": trace_id,
        "incident_id": state.get("incident_id"),
        "node": node,
        "status": status,
        "timestamp": _utc_now(),
        "duration_ms": round(duration_ms, 3),
        "output_keys": list(output_keys),
    }
    if error is not None:
        event["error"] = error
    events.append(event)
    return events


def traced_node(
    node_name: str,
    node: Callable[[InvestigationState], dict[str, Any]],
) -> Callable[[InvestigationState], dict[str, Any]]:
    """Wrap a graph node with lightweight structured execution tracing.

    This is intentionally dependency-free so local development and tests do not
    require an observability backend. The emitted events can later be exported
    to OpenTelemetry, LangSmith, or another backend without changing agents.
    """

    def run(state: InvestigationState) -> dict[str, Any]:
        trace_id = str(uuid4())
        started = perf_counter()
        try:
            result = node(state)
        except Exception as exc:
            duration_ms = (perf_counter() - started) * 1000
            return_update = {
                "observability_events": _append_trace(
                    state,
                    trace_id=trace_id,
                    node=node_name,
                    status="error",
                    duration_ms=duration_ms,
                    error=f"{type(exc).__name__}: {exc}",
                )
            }
            # Preserve the failure event on the exception object for callers
            # that inspect it, while keeping normal graph behavior unchanged.
            setattr(exc, "sentinelops_trace_event", return_update["observability_events"][-1])
            raise

        duration_ms = (perf_counter() - started) * 1000
        return {
            **result,
            "observability_events": _append_trace(
                state,
                trace_id=trace_id,
                node=node_name,
                status="ok",
                duration_ms=duration_ms,
                output_keys=tuple(sorted(result.keys())),
            ),
        }

    return run
