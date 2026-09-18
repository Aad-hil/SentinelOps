import argparse

from langgraph.types import Command

from graph.investigation import build_investigation_graph
from memory.checkpoint import create_checkpointer
from memory.persistence import persist_completed_investigation
from memory.postgres import PostgresIncidentMemoryRepository
from memory.semantic import QdrantIncidentMemoryRepository
from simulator.scenarios import build_incident_001_evidence, build_incident_002_evidence

_SCENARIOS = {
    "INC-001": build_incident_001_evidence,
    "INC-002": build_incident_002_evidence,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m simulator",
        description="Run a SentinelOps incident investigation.",
    )
    parser.add_argument(
        "--incident-id",
        required=True,
        choices=tuple(_SCENARIOS),
        help="Incident scenario to investigate.",
    )
    return parser


def run_investigation(
    incident_id: str,
    repository=None,
    semantic_repository=None,
    approval: dict | None = None,
):
    """Run one incident and optionally persist its long-term memory."""
    try:
        evidence = _SCENARIOS[incident_id]()
    except KeyError as exc:
        raise ValueError(f"Unsupported incident: {incident_id}") from exc

    initial_state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }
    checkpointer = create_checkpointer()
    graph = build_investigation_graph(
        checkpointer=checkpointer,
        incident_memory_repository=semantic_repository,
    )
    config = {"configurable": {"thread_id": evidence.incident.incident_id}}
    state = graph.invoke(initial_state, config=config)

    if approval is not None and state.get("__interrupt__"):
        state = graph.invoke(Command(resume=approval), config=config)

    if repository is not None:
        persist_completed_investigation(
            state,
            repository,
            semantic_repository=semantic_repository,
        )

    return state


def _print_report(state: dict) -> None:
    incident = state["evidence"].incident
    print("\n=== SentinelOps Investigation ===")
    print(f"Incident: {incident.incident_id}")
    print(f"Service: {incident.service}")
    print(f"Severity: {incident.severity}")
    print(f"Title: {incident.title}")
    print(f"Status: {state.get('investigation_status', 'unknown')}")

    print("\n--- Investigation Plan ---")
    for task in state.get("plan", []):
        print(f"- {task}")

    print("\n--- Historical Incidents ---")
    historical = state.get("historical_incidents", [])
    if not historical:
        print("- No relevant historical incidents found.")
    for match in historical:
        print(
            f"- {match.incident_id}: {match.title} "
            f"(similarity={match.score:.3f})"
        )
        if match.root_cause_statement:
            print(f"  Historical root cause: {match.root_cause_statement}")
        if match.recovery_action:
            print(f"  Historical recovery: {match.recovery_action}")

    print("\n--- Agent Findings ---")
    for finding in state.get("findings", []):
        print(f"[{finding.agent}] {finding.summary}")
        if finding.evidence:
            print(f"  Evidence: {', '.join(finding.evidence)}")
        print(f"  Confidence: {finding.confidence:.3f}")

    print("\n--- Competing Hypotheses ---")
    for hypothesis in state.get("hypotheses", []):
        print(
            f"{hypothesis.hypothesis_id}: {hypothesis.statement} "
            f"(confidence={hypothesis.confidence:.3f}, status={hypothesis.status})"
        )

    critique = state.get("critique")
    if critique is not None:
        print("\n--- Critic ---")
        print(f"Hypothesis: {critique.hypothesis_id}")
        print(f"Challenge: {critique.challenge}")
        if critique.missing_evidence:
            print(f"Missing evidence: {', '.join(critique.missing_evidence)}")
        if critique.contradictions:
            print(f"Contradictions: {', '.join(critique.contradictions)}")
        print(f"Confidence: {critique.confidence:.3f}")

    adjudication = state.get("adjudication")
    if adjudication is not None:
        print("\n--- Adjudication ---")
        print(f"Hypothesis: {adjudication.hypothesis_id}")
        print(f"Rationale: {adjudication.rationale}")
        print(f"Temporal support: {adjudication.temporal_support}")
        print(f"Causal support: {adjudication.causal_support}")
        print(f"Recovery support: {adjudication.recovery_support}")
        if adjudication.alternative_gaps:
            print(f"Alternative gaps: {', '.join(adjudication.alternative_gaps)}")
        print(f"Confidence: {adjudication.confidence:.3f}")

    safety = state.get("safety_decision")
    if safety is not None:
        print("\n--- Safety Review ---")
        print(f"Decision: {safety.decision}")
        print(f"Risk level: {safety.risk_level}")
        print(f"Approval required: {safety.approval_required}")
        print(f"Rationale: {safety.rationale}")
        if safety.blocked_steps:
            print(f"Blocked steps: {', '.join(safety.blocked_steps)}")
        if safety.evidence_gaps:
            print(f"Evidence gaps: {', '.join(safety.evidence_gaps)}")
        print(f"Approval status: {state.get('approval_status', 'unknown')}")

    print(f"\nNormalized evidence items: {len(state.get('evidence_items', []))}")


def main() -> int:
    args = build_parser().parse_args()
    repository = PostgresIncidentMemoryRepository()
    semantic_repository = QdrantIncidentMemoryRepository()
    state = run_investigation(
        args.incident_id,
        repository=repository,
        semantic_repository=semantic_repository,
    )
    _print_report(state)

    if state.get("__interrupt__"):
        print("\n=== Human Approval Required ===")
        print("Recovery actions have NOT been executed.")
        while True:
            decision = input("Approve recovery plan? [y/n]: ").strip().lower()
            if decision in {"y", "yes", "n", "no"}:
                break
            print("Please enter y or n.")
        reviewer = input("Reviewer name: ").strip()
        while not reviewer:
            print("Reviewer name is required.")
            reviewer = input("Reviewer name: ").strip()

        state = run_investigation(
            args.incident_id,
            repository=repository,
            semantic_repository=semantic_repository,
            approval={"approved": decision in {"y", "yes"}, "reviewer": reviewer},
        )
        _print_report(state)

    print(f"\nLong-term memory: saved {args.incident_id} to PostgreSQL")
    print("Semantic memory: indexed in Qdrant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
