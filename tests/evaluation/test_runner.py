"""Redshift-only benchmark compatibility tests."""

from evaluation.runner import EvaluationReport, format_report, run_benchmark


def test_benchmark_evaluates_twelve_redshift_cases():
    report = run_benchmark()
    assert isinstance(report, EvaluationReport)
    assert len(report.cases) == 12
    assert 0 <= report.top1_accuracy <= 1
    assert 0 <= report.top3_recall <= 1
    assert all(case.expected_hypothesis_id.startswith("RSH") for case in report.cases)


def test_benchmark_report_is_human_readable():
    output = format_report(run_benchmark())
    assert "SentinelOps Redshift Evaluation" in output
    assert "Cases: 12" in output
    assert "Top-1 hypothesis accuracy" in output
