"""Redshift-specific candidate hypotheses for the SentinelOps migration.

These definitions are descriptive signals for later scoring integration. They
are not ground truth and do not imply that a keyword match proves causality.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RedshiftHypothesisDefinition:
    hypothesis_id: str
    name: str
    statement: str
    trigger_signals: tuple[str, ...]
    mechanism_signals: tuple[str, ...]
    impact_signals: tuple[str, ...]
    evidence_sources: tuple[str, ...]


REDSHIFT_HYPOTHESES: tuple[RedshiftHypothesisDefinition, ...] = (
    RedshiftHypothesisDefinition(
        "RSH1", "WLM Queue Contention",
        "Concurrent workloads saturated a Redshift workload-management queue.",
        ("workload", "concurrency", "queue", "priority"),
        ("queued", "slot", "wlm", "queue wait"),
        ("query latency", "timeout", "query error"),
        ("redshift_system_views", "cloudwatch", "query_history"),
    ),
    RedshiftHypothesisDefinition(
        "RSH2", "SQL or Query-Plan Regression",
        "A SQL change or inefficient execution plan increased query work.",
        ("query change", "sql revision", "query version"),
        ("scan", "join", "query plan", "spill", "runtime"),
        ("latency", "timeout", "query error", "cpu"),
        ("query_history", "explain_plan", "cloudwatch", "deployment"),
    ),
    RedshiftHypothesisDefinition(
        "RSH3", "Compute Capacity Pressure",
        "Workload demand exceeded available Redshift compute capacity.",
        ("workload growth", "traffic", "concurrency", "capacity"),
        ("cpu", "queue", "compute", "headroom"),
        ("latency", "timeout", "query error"),
        ("cloudwatch", "redshift_cluster_metrics", "query_history"),
    ),
    RedshiftHypothesisDefinition(
        "RSH4", "COPY or UNLOAD Data Pipeline Failure",
        "A Redshift data load or unload operation failed or degraded.",
        ("copy", "unload", "load job", "s3 object"),
        ("load error", "file format", "manifest", "throughput"),
        ("failed file", "load failure", "query error", "job delay"),
        ("redshift_load_history", "stl_load_errors", "s3", "cloudtrail"),
    ),
    RedshiftHypothesisDefinition(
        "RSH5", "Spectrum or External Data Failure",
        "Spectrum or external catalog/data access failed for a Redshift query.",
        ("spectrum", "external schema", "glue catalog"),
        ("catalog lookup", "s3 access", "partition", "external table"),
        ("query error", "scan failure", "latency"),
        ("spectrum_query_history", "glue", "s3", "cloudtrail"),
    ),
    RedshiftHypothesisDefinition(
        "RSH6", "Table Design or Statistics Regression",
        "Table distribution, sort design, or stale statistics increased query cost.",
        ("table change", "maintenance", "statistics", "distribution"),
        ("data skew", "unsorted", "stale statistics", "scan"),
        ("query latency", "cpu", "query runtime"),
        ("svv_table_info", "query_history", "analyze_history", "cloudwatch"),
    ),
    RedshiftHypothesisDefinition(
        "RSH7", "Query Spill or Storage Pressure",
        "A query exceeded available execution memory and spilled intermediate data.",
        ("large query", "workload change", "join"),
        ("disk spill", "temporary storage", "intermediate result"),
        ("query latency", "timeout", "query error"),
        ("query_monitoring_rules", "query_history", "cloudwatch"),
    ),
    RedshiftHypothesisDefinition(
        "RSH8", "IAM or KMS Authorization Failure",
        "An IAM role, S3 policy, or KMS key policy blocked a Redshift workflow.",
        ("iam policy", "role change", "kms policy", "permission change"),
        ("access denied", "assume role", "decrypt", "s3 authorization"),
        ("copy failure", "unload failure", "spectrum error"),
        ("cloudtrail", "iam", "kms", "s3", "redshift"),
    ),
    RedshiftHypothesisDefinition(
        "RSH9", "VPC or Client Connectivity Failure",
        "A network path or client connection change disrupted Redshift access.",
        ("security group", "route", "network change", "endpoint"),
        ("connection refused", "dns", "routing", "connect timeout"),
        ("connection failure", "client timeout", "query unavailable"),
        ("vpc_flow_logs", "cloudwatch", "client_logs", "cloudtrail"),
    ),
    RedshiftHypothesisDefinition(
        "RSH10", "Cluster Health or Maintenance Event",
        "A Redshift cluster event or maintenance operation disrupted query service.",
        ("maintenance", "node replacement", "cluster event", "failover"),
        ("cluster unavailable", "node health", "recovery", "restart"),
        ("query error", "unavailable", "latency"),
        ("redshift_cluster_events", "describe_clusters", "cloudwatch"),
    ),
    RedshiftHypothesisDefinition(
        "RSH11", "Data Sharing Producer or Consumer Failure",
        "A data-share state or authorization issue blocked consumer access.",
        ("data share", "producer change", "consumer authorization"),
        ("share state", "grant", "namespace", "consumer access"),
        ("query error", "access failure", "unavailable"),
        ("redshift_datashares", "redshift_query_history", "cloudtrail"),
    ),
    RedshiftHypothesisDefinition(
        "RSH12", "Unknown or Compound Redshift Workload Failure",
        "Available evidence is insufficient or supports multiple interacting causes.",
        ("unknown", "unclassified", "multiple signals"),
        ("ambiguous", "conflicting evidence", "incomplete telemetry"),
        ("query error", "latency", "workload degradation"),
        ("all_available_evidence",),
    ),
)


def get_redshift_hypothesis(hypothesis_id: str) -> RedshiftHypothesisDefinition:
    for hypothesis in REDSHIFT_HYPOTHESES:
        if hypothesis.hypothesis_id == hypothesis_id:
            return hypothesis
    raise KeyError(f"Unknown Redshift hypothesis: {hypothesis_id}")
