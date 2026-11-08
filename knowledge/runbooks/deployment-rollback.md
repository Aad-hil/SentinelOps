# Redshift Change and Configuration Review

Changes relevant to Redshift investigations include WLM configuration, workload priorities, SQL/query revisions, cluster resize or maintenance, table design, statistics/maintenance operations, IAM role associations, KMS policies, external schemas, S3 data paths, VPC routes and security groups.

## Investigation use

Compare the change timestamp with the first abnormal Redshift query, WLM, load, cluster, or dependency signal. Inspect the exact changed setting and affected workload.

Change timing is correlation evidence, not proof of causation. Require telemetry or system-view evidence showing the expected mechanism and impact. Synthetic simulator change records are explicitly labeled and are not actual AWS change events.
