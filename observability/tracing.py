from __future__ import annotations

import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    Status,
    StatusCode,
    TraceFlags,
    set_span_in_context,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from graph.state import InvestigationState

_TRACER_NAME = "sentinelops"
_provider_configured = False
_HEX_TRACE_ID_LENGTH = 32
_HEX_SPAN_ID_LENGTH = 16


def configure_telemetry(*, console_export: bool | None = None) -> None:
    """Configure the OpenTelemetry SDK without requiring a paid backend."""
    global _provider_configured
    if _provider_configured:
        return

    resource = Resource.create({"service.name": "sentinelops"})
    provider = TracerProvider(resource=resource)

    if console_export is None:
        console_export = os.getenv("SENTINELOPS_OTEL_CONSOLE", "").lower() in {
            "1",
            "true",
            "yes",
        }

    if console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    otlp_endpoint = os.getenv("SENTINELOPS_OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            )
        )

    trace.set_tracer_provider(provider)
    _provider_configured = True


def get_tracer():
    """Return the SentinelOps OpenTelemetry tracer."""
    return trace.get_tracer(_TRACER_NAME)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_trace_context() -> tuple[str, str]:
    """Create serializable trace/span identifiers for LangGraph state."""
    trace_id = f"{uuid4().int:032x}"
    span_id = f"{uuid4().int & ((1 << 64) - 1):016x}"
    return trace_id, span_id


def _span_context_from_state(state: InvestigationState) -> tuple[Any, str, str]:
    """Restore a persisted parent context from serializable graph state."""
    trace_id = state.get("otel_trace_id")
    parent_span_id = state.get("otel_parent_span_id")

    if not trace_id or not parent_span_id:
        trace_id, parent_span_id = _new_trace_context()

    span_context = SpanContext(
        trace_id=int(trace_id, 16),
        span_id=int(parent_span_id, 16),
        is_remote=True,
        trace_flags=TraceFlags(0x01),
    )
    return set_span_in_context(NonRecordingSpan(span_context)), trace_id, parent_span_id


def initialize_investigation_trace(
    tracer=None,
) -> tuple[Any, str, str]:
    """Start a real investigation root span and return its serializable context."""
    node_tracer = tracer or get_tracer()
    root_span = node_tracer.start_span("sentinelops.investigation")
    span_context = root_span.get_span_context()

    if not span_context.is_valid:
        root_span.end()
        trace_id, span_id = _new_trace_context()
        return None, trace_id, span_id

    trace_id = f"{span_context.trace_id:0{_HEX_TRACE_ID_LENGTH}x}"
    span_id = f"{span_context.span_id:0{_HEX_SPAN_ID_LENGTH}x}"
    return root_span, trace_id, span_id


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
    *,
    tracer=None,
) -> Callable[[InvestigationState], dict[str, Any]]:
    """Wrap a graph node with structured events and a propagated OTel parent."""
    node_tracer = tracer or get_tracer()

    def run(state: InvestigationState) -> dict[str, Any]:
        parent_context, trace_id, parent_span_id = _span_context_from_state(state)
        started = perf_counter()

        with node_tracer.start_as_current_span(
            f"sentinelops.node.{node_name}",
            context=parent_context,
        ) as span:
            actual_trace_id = f"{span.get_span_context().trace_id:0{_HEX_TRACE_ID_LENGTH}x}"
            span.set_attribute("sentinelops.incident_id", state.get("incident_id", ""))
            span.set_attribute("sentinelops.node", node_name)
            span.set_attribute("sentinelops.trace_id", actual_trace_id)
            span.set_attribute("sentinelops.parent_span_id", parent_span_id)

            try:
                result = node(state)
            except Exception as exc:
                duration_ms = (perf_counter() - started) * 1000
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                setattr(
                    exc,
                    "sentinelops_trace_event",
                    _append_trace(
                        state,
                        trace_id=actual_trace_id,
                        node=node_name,
                        status="error",
                        duration_ms=duration_ms,
                        error=f"{type(exc).__name__}: {exc}",
                    )[-1],
                )
                raise

            duration_ms = (perf_counter() - started) * 1000
            span.set_status(Status(StatusCode.OK))
            span.set_attribute("sentinelops.duration_ms", duration_ms)
            span.set_attribute("sentinelops.output_key_count", len(result))

            return {
                **result,
                "otel_trace_id": actual_trace_id,
                "otel_parent_span_id": parent_span_id,
                "observability_events": _append_trace(
                    state,
                    trace_id=actual_trace_id,
                    node=node_name,
                    status="ok",
                    duration_ms=duration_ms,
                    output_keys=tuple(sorted(result.keys())),
                ),
            }

    return run
