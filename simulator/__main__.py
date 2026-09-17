import argparse

from graph.investigation import build_investigation_graph
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


def run_investigation(incident_id: str):
    """Build agent-facing evidence and run the investigation graph."""
    try:
        evidence = _SCENARIOS[incident_id]()
    except KeyError as exc:
        raise ValueError(f"Unsupported incident: {incident_id}") from exc

    initial_state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }
    return build_investigation_graph().invoke(initial_state)


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

    print(f"\nNormalized evidence items: {len(state.get('evidence_items', []))}")


def main() -> int:
    args = build_parser().parse_args()
    state = run_investigation(args.incident_id)
    _print_report(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
