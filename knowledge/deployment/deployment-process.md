# Redshift Change Validation

## Before change

Validate SQL and EXPLAIN plans, WLM behavior, workload concurrency, table design/statistics, COPY/UNLOAD options, external schema access, IAM/KMS permissions, and network reachability in a representative non-production environment.

## After change

Monitor query execution and queue time, WLM queue depth, compute utilization, spill, load errors, cluster events, and relevant S3/Glue/IAM/KMS/VPC signals.

## Regression detection

Preserve before/after evidence around the change window. A temporal association is not sufficient: establish the Redshift-specific mechanism and workload impact before attributing root cause.
