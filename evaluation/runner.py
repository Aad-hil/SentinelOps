"""Run the SentinelOps investigation benchmark without external persistence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from evaluation.incident_metrics import (
    concept_coverage,
    recovery_action_concept_match,
    text_concept_match,
)
from graph.investigation import build_investigation_graph
from simulator.benchmark import build_all_benchmark_incidents


_CASES_PATH = Path(__file__).with_name("incident_cases.json")


def _case_category(incident_id: str) -> str:
    cases = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    for case in cases:
        if case["incident_id"] == incident_id:
            return case["category"]
    raise KeyError(f"Unknown benchmark incident: {incident_id}")


# These groups describe the concepts represented by the synthetic benchmark
# rather than copying the wording of the public availability reports.
_EVIDENCE_CONCEPTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "database_connection_pool": (
        ("pool", "connection", "connections"),
        ("50 to 20", "pool_size", "capacity"),
        ("wait time", "connection wait", "latency"),
    ),
    "deployment_query_database_saturation": (
        ("deployment", "changed", "version"),
        ("query", "operation"),
        ("database", "db"),
        ("cpu", "saturation"),
        ("error", "error rate"),
    ),
    "database_cpu_query_load": (
        ("db_cpu_percent", "database cpu", "cpu"),
        ("Put Manifest", "manifests", "package"),
        ("query", "latency"),
    ),
    "query_lock_contention": (
        ("query change", "frequently-used query", "query"),
        ("lock", "contention", "lock_wait"),
        ("resource", "cpu"),
        ("latency", "query_latency"),
    ),
    "schema_change_database_contention": (
        ("schema", "migration"),
        ("query", "load"),
        ("connection", "db_connection"),
        ("resource", "contention"),
        ("latency", "error"),
    ),
    "maintenance_slow_query": (
        ("long-running", "query", "long_running"),
        ("maintenance", "database maintenance"),
        ("cpu", "pressure"),
        ("latency", "query_latency"),
    ),
    "expensive_query_write_latency": (
        ("write", "transaction"),
        ("db_query_cpu", "cpu"),
        ("write latency", "db_write_latency"),
        ("timeout", "error"),
    ),
    "database_connection_failure": (
        ("connection", "db_connection"),
        ("primary", "database"),
        ("latency", "request_latency"),
        ("error", "failure"),
    ),
    "database_failover": (
        ("primary", "db_primary"),
        ("failover", "attempt"),
        ("configuration", "database_version"),
        ("crash", "health"),
    ),
    "peak_load_database_headroom": (
        ("request_rate", "traffic", "load"),
        ("headroom", "db_headroom"),
        ("cpu", "database"),
        ("query", "performance"),
    ),
    "database_migration_permissions": (
        ("migration", "write traffic"),
        ("insert", "write"),
        ("permission", "permissions"),
        ("error", "failure"),
    ),
    "inefficient_query_background_load": (
        ("api_request_rate", "api", "request"),
        ("query", "inefficient"),
        ("queue", "background", "webhook"),
        ("latency", "resource"),
    ),
    "database_replication_lag_query_amplification": (
        ("token_request_rate", "token", "request"),
        ("replication", "lag"),
        ("query", "amplification"),
        ("replica", "database"),
    ),
    "data_store_upgrade_resource_contention": (
        ("upgrade", "version"),
        ("resource", "contention"),
        ("query", "latency"),
        ("timeout", "error"),
    ),
    "migration_peak_load_connection_saturation": (
        ("migration", "active"),
        ("traffic", "peak", "request_rate"),
        ("connection", "db_connection"),
        ("contention", "latency"),
    ),
}


_ROOT_CAUSE_CONCEPTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "database_connection_pool": (("database", "db"), ("connection", "pool"), ("exhaustion", "capacity")),
    "deployment_query_database_saturation": (("deployment",), ("query",), ("database", "db"), ("saturation", "cpu")),
    "database_cpu_query_load": (("query",), ("database", "db"), ("cpu", "load"), ("traffic", "request")),
    "query_lock_contention": (("query",), ("lock", "contention"), ("resource", "exhaustion")),
    "schema_change_database_contention": (("schema", "migration"), ("query", "load"), ("contention", "connection")),
    "maintenance_slow_query": (("slow", "long-running", "query"), ("maintenance",), ("database", "db")),
    "expensive_query_write_latency": (("expensive", "write", "transaction"), ("query",), ("timeout", "latency")),
    "database_connection_failure": (("connection", "database"), ("primary",), ("failure", "error")),
    "database_failover": (("database",), ("primary", "crash"), ("failover",), ("configuration", "version")),
    "peak_load_database_headroom": (("traffic", "load"), ("database",), ("headroom",), ("query",)),
    "database_migration_permissions": (("migration", "cluster"), ("insert", "write"), ("permission",)),
    "inefficient_query_background_load": (("query",), ("api", "request"), ("background", "queue", "webhook")),
    "database_replication_lag_query_amplification": (("token", "request"), ("query",), ("replication", "lag")),
    "data_store_upgrade_resource_contention": (("upgrade", "version"), ("data-store", "database"), ("contention",), ("query",)),
    "migration_peak_load_connection_saturation": (("migration",), ("traffic", "peak"), ("connection",), ("contention",)),
}


_RECOVERY_CONCEPTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "database_connection_pool": (("pool", "connection", "capacity"), ("rollback",)),
    "deployment_query_database_saturation": (("rollback",), ("deployment",)),
    "database_cpu_query_load": (("throttle", "throttling"), ("restart",), ("database", "front-end")),
    "query_lock_contention": (("disable", "feature flag"), ("query", "refactor")),
    "schema_change_database_contention": (("migration",), ("revert", "stable")),
    "maintenance_slow_query": (("kill", "terminate"), ("query",), ("restart", "database")),
    "expensive_query_write_latency": (("block", "expensive"), ("query",), ("endpoint",)),
    "database_connection_failure": (("restart", "database"), ("migrate", "platform")),
    "database_failover": (("configuration",), ("custom", "vulnerable")),
    "peak_load_database_headroom": (("failover",), ("load", "throttle"), ("query", "optimize")),
    "database_migration_permissions": (("revert", "old cluster"), ("permission",)),
    "inefficient_query_background_load": (("query", "fix"), ("rate", "limit", "throttle"), ("queue",)),
    "database_replication_lag_query_amplification": (("prevent", "overload"), ("query",)),
    "data_store_upgrade_resource_contention": (("rollback", "stable"),),
    "migration_peak_load_connection_saturation": (("pause", "migration"), ("throttle",), ("recover",)),
}


@dataclass(frozen=True)
class IncidentEvaluation:
    incident_id: str
    status: str
    top1_hypothesis_accuracy: float | None
    top3_hypothesis_recall: float | None
    root_cause_concept_match: float
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
    def mean_root_cause_concept_match(self) -> float:
        return mean(item.root_cause_concept_match for item in self.incidents) if self.incidents else 0.0

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

    expected_id = scenario.incident.incident_id == "INC-002"
    root_accuracy = 1.0 if expected_id and predicted_ids and predicted_ids[0] == "H1" else (0.0 if expected_id else None)
    top3_recall = 1.0 if expected_id and "H1" in predicted_ids[:3] else (0.0 if expected_id else None)

    evidence_texts = [item.observation for item in state.get("evidence_items", [])]
    case_category = _case_category(scenario.incident.incident_id)

    top_statement = hypotheses[0].statement if hypotheses else ""
    root_match = text_concept_match(top_statement, _ROOT_CAUSE_CONCEPTS[case_category])
    evidence_match = concept_coverage(evidence_texts, _EVIDENCE_CONCEPTS[case_category])
    recovery_match = recovery_action_concept_match(
        _recovery_actions(state),
        _RECOVERY_CONCEPTS[case_category],
    )

    return IncidentEvaluation(
        incident_id=scenario.incident.incident_id,
        status=state.get("investigation_status", "unknown"),
        top1_hypothesis_accuracy=root_accuracy,
        top3_hypothesis_recall=top3_recall,
        root_cause_concept_match=root_match,
        evidence_coverage=evidence_match,
        recovery_match=recovery_match,
        duration_seconds=duration,
    )


def run_benchmark() -> EvaluationReport:
    """Evaluate all 15 deterministic benchmark scenarios locally."""
    graph = build_investigation_graph(checkpointer=None, incident_memory_repository=None)
    results = tuple(
        evaluate_incident(graph, scenario)
        for scenario in build_all_benchmark_incidents()
    )
    return EvaluationReport(incidents=results)


def format_report(report: EvaluationReport) -> str:
    """Render a compact human-readable benchmark report."""
    lines = [
        "=== SentinelOps Evaluation ===",
        f"Incidents: {report.incident_count}",
        f"Completed/awaiting approval: {report.completed_count}",
        f"Mean root-cause concept match: {report.mean_root_cause_concept_match:.3f}",
        f"Mean evidence coverage: {report.mean_evidence_coverage:.3f}",
        f"Mean recovery match: {report.mean_recovery_match:.3f}",
        f"Mean duration: {report.mean_duration_seconds:.3f}s",
        "",
        "Incident results:",
    ]
    for item in report.incidents:
        root = f"{item.top1_hypothesis_accuracy:.3f}" if item.top1_hypothesis_accuracy is not None else "n/a"
        top3 = f"{item.top3_hypothesis_recall:.3f}" if item.top3_hypothesis_recall is not None else "n/a"
        lines.append(
            f"- {item.incident_id}: status={item.status}, "
            f"top1={root}, top3={top3}, root_cause={item.root_cause_concept_match:.3f}, "
            f"evidence={item.evidence_coverage:.3f}, recovery={item.recovery_match:.3f}, "
            f"duration={item.duration_seconds:.3f}s"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report(run_benchmark()))
