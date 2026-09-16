# Database High CPU Runbook

## Purpose
Investigate sustained CPU saturation on a production database primary.

## Initial checks
- Confirm whether CPU increased gradually or immediately after a deployment.
- Compare primary CPU with replicas or other database nodes.
- Check query execution rate, latency, and the distribution of expensive query fingerprints.
- Check lock waits, queue depth, connection pressure, and storage latency.

## Query investigation
A small number of query fingerprints can account for a large share of database load. Compare query behavior before and after the suspected change window. Useful signals include execution time, calls per minute, rows examined, rows returned, and total database time.

## Correlation
A deployment is a useful lead when a database workload changes shortly afterward, but timing alone does not prove causality. Check whether the affected query pattern appeared or changed after the deployment and whether unrelated traffic or infrastructure events can explain the increase.

## Recovery
If application impact is significant and a recent deployment is strongly correlated with the degradation, follow the deployment rollback procedure after confirming rollback safety.
