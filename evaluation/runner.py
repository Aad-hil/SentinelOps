"""Run the SentinelOps investigation benchmark without external persistence."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from time import perf_counter

from graph.investigation import build_investigation_graph
from evaluation.incident_metrics import (
    evidence_term_coverage,
    recovery_action_contains,
    top1_hypothesis_accuracy,
    top_k_hypothesis_recall,
)
from simulator.benchmark import build_all_benchmark_incidents


@dataclass(frozen=True)
class IncidentEvaluation:
    incident_id: str
    status: str
    top1_hypothesis_accuracy: float | None
    top3_hypothesis_recall: float | None
    evidence_coverage: float
    recovery_match: float
    duration_seconds: float


@dataclass(frozen=True)
class EvaluationReport:
    incidents: tuple[IncidentEvaluation, ...]

    @property
    def incident_count(self) -> int:
        return len(self.incidents)

    @property
    def completed_count(self) -> int:
        return sum(item.status in {"complete", "awaiting_human_approval"} for item in self.incidents)

    @property
    def mean_evidence_coverage(self) -> float:
        return mean(item.evidence_coverage for item in self.incidents) if self.incidents else 0.0

    @property
    def mean_recovery_match(self) -> float:
        return mean(item.recovery_match for item in self.incidents) if self.incidents else 0.0

    @property
    def mean_duration_seconds(self) -> float:
        return mean(item.duration_seconds for item in self.incidents) if self.incidents else 0.0


def _recovery_actions(state: dict) -> list[str]:
    plan = state.get("recovery_plan")
    if plan is None:
        return []
    return [step.action for step in plan.steps]


def evaluate_incident(graph, scenario) -> IncidentEvaluation:
    """Run one benchmark scenario with no persistence or human interrupt."""
    evidence = scenario
    initial_state = {
        "incident_id": evidence.incident.incident_id,
        "incident_summary": evidence.incident.description,
        "evidence": evidence,
    }
    started = perf_counter()
    state = graph.invoke(initial_state)
    duration = perf_counter() - started

    hypotheses = list(state.get("hypotheses", []))
    predicted_ids = [hypothesis.hypothesis_id for hypothesis in hypotheses]
    confidence = {
        hypothesis.hypothesis_id: hypothesis.confidence
        for hypothesis in hypotheses
    }

    expected_id = None
    if scenario.incident.incident_id == "INC-002":
        expected_id = "H1"

    evidence_texts = [
        item.observation
        for item in state.get("evidence_items", [])
    ]

    root_accuracy = (
        top1_hypothesis_accuracy(predicted_ids, expected_id)
        if expected_id
        else None
    )
    top3_recall = (
        top_k_hypothesis_recall(predicted_ids, expected_id, 3)
        if expected_id
        else None
    )

    required = scenario.ground_truth.contributing_factors
    recovery_phrase = scenario.ground_truth.mitigation.split(" or ")[-1]
    recovery_match = recovery_action_contains(
        _recovery_actions(state),
        recovery_phrase,
    )

    return IncidentEvaluation(
        incident_id=scenario.incident.incident_id,
        status=state.get("investigation_status", "unknown"),
        top1_hypothesis_accuracy=root_accuracy,
        top3_hypothesis_recall=top3_recall,
        evidence_coverage=evidence_term_coverage(evidence_texts, required),
        recovery_match=recovery_match,
        duration_seconds=duration,
    )


def run_benchmark() -> EvaluationReport:
    """Evaluate all 15 benchmark scenarios locally."""
    graph = build_investigation_graph(checkpointer=None, incident_memory_repository=None)
    results = tuple(evaluate_incident(graph, scenario) for scenario in build_all_benchmark_incidents())
    return EvaluationReport(incidents=results)


def format_report(report: EvaluationReport) -> str:
    """Render a compact human-readable benchmark report."""
    lines = [
        "=== SentinelOps Evaluation ===",
        f"Incidents: {report.incident_count}",
        f"Completed/awaiting approval: {report.completed_count}",
        f"Mean evidence coverage: {report.mean_evidence_coverage:.3f}",
        f"Mean recovery match: {report.mean_recovery_match:.3f}",
        f"Mean duration: {report.mean_duration_seconds:.3f}s",
        "",
        "Incident results:",
    ]
    for item in report.incidents:
        root = (
            f"{item.top1_hypothesis_accuracy:.3f}"
            if item.top1_hypothesis_accuracy is not None
            else "n/a"
        )
        top3 = (
            f"{item.top3_hypothesis_recall:.3f}"
            if item.top3_hypothesis_recall is not None
            else "n/a"
        )
        lines.append(
            f"- {item.incident_id}: status={item.status}, "
            f"top1={root}, top3={top3}, "
            f"evidence={item.evidence_coverage:.3f}, "
            f"recovery={item.recovery_match:.3f}, "
            f"duration={item.duration_seconds:.3f}s"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report(run_benchmark()))
