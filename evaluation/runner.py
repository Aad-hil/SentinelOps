"""Redshift-only benchmark entry point (legacy generic benchmark retired)."""
from evaluation.redshift_runner import (
    RedshiftCaseResult as IncidentEvaluation,
    RedshiftEvaluationReport as EvaluationReport,
    format_redshift_report as format_report,
    run_redshift_benchmark as run_benchmark,
)


if __name__ == "__main__":
    print(format_report(run_benchmark()))
