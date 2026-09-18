from __future__ import annotations

import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter\nfrom opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from graph.state import InvestigationState

_TRACER_NAME = "sentinelops"
_provider_configured = False


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

    trace.set_tracer_provider(provider)
    _provider_configured = True


def get_tracer():
    """Return the SentinelOps OpenTelemetry tracer."""
    return trace.get_tracer(_TRACER_NAME)


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
    *,
    tracer=None,
) -> Callable[[InvestigationState], dict[str, Any]]:
    """Wrap a graph node with structured events and an OpenTelemetry span."""
    node_tracer = tracer or get_tracer()

    def run(state: InvestigationState) -> dict[str, Any]:
        trace_id = str(uuid4())
        started = perf_counter()

        with node_tracer.start_as_current_span(
            f"sentinelops.node.{node_name}"
        ) as span:
            span.set_attribute("sentinelops.incident_id", state.get("incident_id", ""))
            span.set_attribute("sentinelops.node", node_name)
            span.set_attribute("sentinelops.trace_id", trace_id)

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
                        trace_id=trace_id,
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
