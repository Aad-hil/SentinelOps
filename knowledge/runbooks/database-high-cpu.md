# Amazon Redshift Capacity and WLM Runbook

## Purpose

Investigate Redshift workload latency, queueing, or resource saturation.

## Initial checks

- Inspect WLM queue wait, queued queries, service class, priorities and concurrency limits.
- Compare query execution time with queue wait time; do not conflate them.
- Inspect CloudWatch Redshift metrics and cluster events for correlated compute pressure.
- Identify top query IDs and workload groups during the incident window.
- Check whether concurrency scaling or a recent WLM/configuration change is relevant.

## Evidence standard

A high CPU or queue metric is an impact signal, not a complete cause. Establish which workload or WLM configuration changed and whether it precedes the queue/latency increase. Consider inefficient SQL and capacity pressure as alternatives.

## Recovery boundary

Recommend query prioritization, workload isolation, or a reversible WLM adjustment only when supported by evidence. WLM changes and query cancellation require operator review and human approval.
