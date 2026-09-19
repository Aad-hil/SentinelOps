"""Tests for the local 15-incident evaluation runner."""

from evaluation.runner import EvaluationReport, format_report, run_benchmark


def test_benchmark_runner_evaluates_all_fifteen_incidents() -> None:
    report = run_benchmark()

    assert isinstance(report, EvaluationReport)
    assert report.incident_count == 15
    assert len(report.incidents) == 15
    assert all(item.status for item in report.incidents)
    assert all(0.0 <= item.evidence_coverage <= 1.0 for item in report.incidents)
    assert all(0.0 <= item.recovery_match <= 1.0 for item in report.incidents)


def test_benchmark_report_is_human_readable() -> None:
    report = EvaluationReport(incidents=())
    output = format_report(report)

    assert "SentinelOps Evaluation" in output
    assert "Incidents: 0" in output
