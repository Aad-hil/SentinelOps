from dataclasses import dataclass

from graph.investigation import build_investigation_graph
from rag.retrieval import RetrievalResult
from simulator.scenarios import build_incident_002_evidence


@dataclass
class FakeRetriever:
    calls: list[tuple[str, int]]

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        self.calls.append((query, top_k))
        return [
            RetrievalResult(
                content="Use deployment rollback when a new deployment introduces a database regression.",
                source="runbooks/deployment-rollback.md",
                category="runbook",
                chunk_id="rollback-001",
                score=0.91,
                metadata={},
            )
        ]


def test_investigation_graph_collects_from_three_specialist_agents():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()

    result = graph.invoke(
        {
            "incident_id": evidence.incident.incident_id,
            "incident_summary": evidence.incident.description,
            "evidence": evidence,
        }
    )

    assert result["investigation_status"] == "complete"
    assert result["plan"] == [
        "telemetry",
        "knowledge",
        "deployment",
        "root_cause",
        "critic",
    ]
    assert result["completed_tasks"] == [
        "telemetry",
        "knowledge",
        "deployment",
        "root_cause",
        "critic",
    ]
    assert [finding.agent for finding in result["findings"]] == [
        "telemetry",
        "knowledge",
        "deployment",
        "root_cause",
        "critic",
    ]


def test_agents_produce_independent_findings():
    evidence = build_incident_002_evidence()
    graph = build_investigation_graph()
    result = graph.invoke({"evidence": evidence})
    findings = {finding.agent: finding for finding in result["findings"]}

    assert findings["telemetry"].category == "telemetry"
    assert findings["knowledge"].category == "knowledge"
    assert findings["deployment"].category == "deployment"
    assert findings["root_cause"].category == "hypothesis_evaluation"
    assert findings["critic"].category == "critique"
    assert findings["telemetry"].summary != findings["deployment"].summary


def test_knowledge_agent_uses_injected_rag_tool():
    evidence = build_incident_002_evidence()
    retriever = FakeRetriever(calls=[])
    graph = build_investigation_graph()

    result = graph.invoke({"evidence": evidence, "knowledge_retriever": retriever})

    assert len(retriever.calls) == 1
    query, top_k = retriever.calls[0]
    assert evidence.incident.title in query
    assert top_k == 5

    knowledge_finding = next(
        finding for finding in result["findings"] if finding.agent == "knowledge"
    )
    assert knowledge_finding.evidence == ("runbooks/deployment-rollback.md",)
    assert knowledge_finding.confidence == 0.7
