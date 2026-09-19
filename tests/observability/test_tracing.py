from graph.investigation import build_investigation_graph
from simulator.scenarios import build_incident_002_evidence
from observability.tracing import traced_node


def test_traced_node_records_successful_execution():
    def node(state):
        return {"messages": ["done"], "result": 42}

    result = traced_node("example", node)({"incident_id": "INC-TEST"})

    event = result["observability_events"][0]
    assert event["incident_id"] == "INC-TEST"
    assert event["node"] == "example"
    assert event["status"] == "ok"
    assert event["duration_ms"] >= 0
    assert event["output_keys"] == ["messages", "result"]
    assert event["trace_id"]


def test_traced_node_preserves_existing_events():
    def node(state):
        return {"messages": ["next"]}

    state = {
        "incident_id": "INC-TEST",
        "observability_events": [{"node": "previous", "status": "ok"}],
    }
    result = traced_node("example", node)(state)

    assert len(result["observability_events"]) == 2
    assert result["observability_events"][0]["node"] == "previous"
    assert result["observability_events"][1]["node"] == "example"


def test_investigation_graph_emits_trace_for_each_investigation_node():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()
    result = graph.invoke(
        {
            "incident_id": evidence.incident.incident_id,
            "incident_summary": evidence.incident.description,
            "evidence": evidence,
        }
    )

    traced_nodes = [event["node"] for event in result["observability_events"]]
    assert traced_nodes == [
        "historical_memory",
        "supervisor",
        "telemetry",
        "supervisor",
        "knowledge",
        "supervisor",
        "deployment",
        "supervisor",
        "root_cause",
        "supervisor",
        "critic",
        "supervisor",
        "adjudication",
        "supervisor",
        "recovery",
        "supervisor",
        "safety",
        "supervisor",
    ]
    assert all(event["status"] == "ok" for event in result["observability_events"])
    assert all(event["trace_id"] for event in result["observability_events"])


def test_traced_node_emits_an_opentelemetry_span():
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "sentinelops-test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("sentinelops-test")

    def node(state):
        return {"result": "ok"}

    result = traced_node("otel-example", node, tracer=tracer)({"incident_id": "INC-OTEL"})
    spans = exporter.get_finished_spans()

    assert result["observability_events"][0]["status"] == "ok"
    assert len(spans) == 1
    assert spans[0].name == "sentinelops.node.otel-example"
    assert spans[0].attributes["sentinelops.incident_id"] == "INC-OTEL"
    assert spans[0].attributes["sentinelops.node"] == "otel-example"



def test_configure_telemetry_can_enable_an_otlp_exporter(monkeypatch):
    monkeypatch.setenv("SENTINELOPS_OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    monkeypatch.setenv("SENTINELOPS_OTEL_CONSOLE", "false")

    import observability.tracing as tracing

    tracing._provider_configured = False
    tracing.configure_telemetry()

    assert tracing._provider_configured is True


def test_traced_nodes_share_one_trace_context():
    def first(state):
        return {"first": True}

    def second(state):
        return {"second": True}

    state = {"incident_id": "INC-TRACE"}
    first_result = traced_node("first", first)(state)
    second_result = traced_node("second", second)(first_result)

    assert first_result["otel_trace_id"] == second_result["otel_trace_id"]
    assert first_result["otel_parent_span_id"] == second_result["otel_parent_span_id"]
    assert first_result["observability_events"][0]["trace_id"] == second_result["observability_events"][1]["trace_id"]


def test_opentelemetry_spans_use_the_same_trace_id_and_shared_parent():
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "sentinelops-test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("sentinelops-test")

    state = {"incident_id": "INC-OTEL-CORRELATION"}
    state = traced_node("one", lambda _: {"one": True}, tracer=tracer)(state)
    state = traced_node("two", lambda _: {"two": True}, tracer=tracer)(state)
    spans = exporter.get_finished_spans()

    assert len(spans) == 2
    assert spans[0].context.trace_id == spans[1].context.trace_id
    assert spans[0].parent is not None
    assert spans[1].parent is not None
    assert spans[0].parent.span_id == spans[1].parent.span_id
