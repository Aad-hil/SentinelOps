"""Synthetic benchmark only; these are not full-graph accuracy claims."""
from evaluation.runner import run_benchmark, format_report


def test_redshift_benchmark_reports_twelve_cases():
    report = run_benchmark()
    assert len(report.cases) == 12
    assert 0 <= report.top1_accuracy <= 1
    assert 0 <= report.top3_recall <= 1
    assert all(case.expected_hypothesis_id.startswith("RSH") for case in report.cases)
    output = format_report(report)
    assert "Cases: 12" in output
    assert "Top-1 hypothesis accuracy" in output
