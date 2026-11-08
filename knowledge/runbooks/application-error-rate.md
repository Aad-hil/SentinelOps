# Redshift Workload Impact Runbook

## Purpose

Investigate service or pipeline errors that may originate in an Amazon Redshift workload or one of its direct dependencies.

## Initial checks

- Identify the affected Redshift cluster/namespace, database, workload group, query, COPY/UNLOAD job, Spectrum table, or data share.
- Correlate client errors with Redshift query/load history and cluster events.
- Distinguish Redshift query failures from client connection, IAM/KMS, S3, or Glue dependency failures.
- Compare first abnormal timestamps across logs, metrics, and traces.

## Dependency failures

S3, Glue, IAM, KMS, and VPC evidence is in scope only when tied to a specific Redshift operation. An application error or generic timeout alone is insufficient to diagnose a Redshift cause.

## Escalation

If evidence does not establish a Redshift-specific cause, classify the incident as unknown/compound (RSH12) and request targeted diagnostics rather than forcing a diagnosis.
