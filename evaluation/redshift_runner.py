"""Evaluate the Redshift hypothesis engine against synthetic scenario labels.

This evaluator intentionally runs the evidence-gathering and hypothesis-ranking
agents directly. Ground-truth labels are read only from the simulator scenario
metadata and are never inserted into the agent state.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from time import perf_counter

from agents.deployment import run_deployment_agent
from agents.root_cause import generate_hypotheses
from agents.telemetry import run_telemetry_agent
from simulator.redshift import build_all_redshift_incidents


_CATEGORY_LABELS = {
    "wlm_queue_contention": "RSH1",
    "sql_query_regression": "RSH2",
    "compute_capacity_pressure": "RSH3",
    "copy_load_failure": "RSH4",
    "spectrum_external_data": "RSH5",
    "table_design_statistics": "RSH6",
    "query_spill_storage_pressure": "RSH7",
    "iam_kms_authorization": "RSH8",
    "vpc_connectivity": "RSH9",
    "cluster_maintenance_health": "RSH10",
    "data_sharing_consumer": "RSH11",
    "unknown_compound": "RSH12",
}


@dataclass(frozen=True)
class RedshiftCaseResult:
    incident_id: str
    expected_hypothesis_id: str
    predicted_hypothesis_id: str | None
    top3_contains_expected: bool
    confidence: float | None
    duration_seconds: float


@dataclass(frozen=True)
class RedshiftEvaluationReport:
    cases: tuple[RedshiftCaseResult, ...]

    @property
    def top1_accuracy(self) -> float:
        return mean(
            item.predicted_hypothesis_id == item.expected_hypothesis_id
            for item in self.cases
        ) if self.cases else 0.0

    @property
    def top3_recall(self) -> float:
        return mean(item.top3_contains_expected for item in self.cases) if self.cases else 0.0

    @property
    def mean_duration_seconds(self) -> float:
        return mean(item.duration_seconds for item in self.cases) if self.cases else 0.0


def run_redshift_benchmark() -> RedshiftEvaluationReport:
    """Run all deterministic Redshift cases without passing labels to agents."""
    results = []
    for scenario in build_all_redshift_incidents():
        started = perf_counter()
        state = {
            "incident_id": scenario.incident.incident_id,
            "incident_summary": scenario.incident.description,
            "evidence": scenario,
        }
        state.update(run_telemetry_agent(state))
        state.update(run_deployment_agent(state))
        hypotheses = generate_hypotheses(state)
        elapsed = perf_counter() - started

        category = scenario.ground_truth.contributing_factors[0]
        expected = _CATEGORY_LABELS[category]
        ranked = [item.hypothesis_id for item in hypotheses]
        results.append(RedshiftCaseResult(
            incident_id=scenario.incident.incident_id,
            expected_hypothesis_id=expected,
            predicted_hypothesis_id=ranked[0] if ranked else None,
            top3_contains_expected=expected in ranked[:3],
            confidence=hypotheses[0].confidence if hypotheses else None,
            duration_seconds=elapsed,
        ))
    return RedshiftEvaluationReport(tuple(results))


def format_redshift_report(report: RedshiftEvaluationReport) -> str:
    lines = [
        "=== SentinelOps Redshift Evaluation ===",
        f"Cases: {len(report.cases)}",
        f"Top-1 hypothesis accuracy: {report.top1_accuracy:.3f}",
        f"Top-3 hypothesis recall: {report.top3_recall:.3f}",
        f"Mean ranking duration: {report.mean_duration_seconds:.4f}s",
        "",
        "Case results:",
    ]
    for item in report.cases:
        confidence = f"{item.confidence:.3f}" if item.confidence is not None else "n/a"
        lines.append(
            f"- {item.incident_id}: expected={item.expected_hypothesis_id}, "
            f"predicted={item.predicted_hypothesis_id or 'n/a'}, "
            f"top3={item.top3_contains_expected}, confidence={confidence}, "
            f"duration={item.duration_seconds:.4f}s"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_redshift_report(run_redshift_benchmark()))
