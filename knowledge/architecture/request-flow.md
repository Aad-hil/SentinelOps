# Redshift Investigation Evidence Flow

1. Identify the Redshift cluster/namespace, database, workload group, query or data movement operation.
2. Collect Redshift query/WLM/load history, cluster events, and relevant CloudWatch metrics.
3. Add dependency evidence from S3, Glue, IAM, KMS, or VPC only when tied to the affected Redshift operation.
4. Normalize timestamps and distinguish trigger, mechanism, impact, and recovery evidence.
5. Rank RSH1-RSH12; preserve unknown/compound classification when the evidence is insufficient.
6. Prepare an evidence-linked recovery proposal and pass it through safety and human approval.

The repository's default simulator is synthetic. It does not collect live AWS telemetry.
