"""Tests for the expanded 15-incident synthetic benchmark."""

from simulator.benchmark import build_all_benchmark_incidents, build_benchmark_incident
from simulator.scenarios import build_benchmark_evidence


def test_all_benchmark_incidents_are_deterministic_and_complete() -> None:
    scenarios = build_all_benchmark_incidents()

    assert len(scenarios) == 15
    assert [scenario.incident.incident_id for scenario in scenarios] == [
        f"INC-{number:03d}" for number in range(1, 16)
    ]

    for scenario in scenarios:
        assert scenario.logs
        assert scenario.metrics
        assert scenario.deployments
        assert scenario.traces
        assert scenario.ground_truth.root_cause


def test_public_benchmark_scenarios_use_synthetic_timestamps() -> None:
    scenarios = build_all_benchmark_incidents()

    for scenario in scenarios[1:]:
        assert scenario.incident.started_at.year == 2026


def test_agent_evidence_does_not_include_ground_truth() -> None:
    evidence = build_benchmark_evidence("INC-004")

    assert not hasattr(evidence, "ground_truth")
    assert evidence.incident.incident_id == "INC-004"


def test_incident_two_keeps_existing_realistic_generator() -> None:
    scenario = build_benchmark_incident("INC-002")

    assert scenario.incident.incident_id == "INC-002"
    assert any("q7f2" in log.message for log in scenario.logs)
