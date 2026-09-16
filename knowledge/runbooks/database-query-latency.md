# Database Query Latency Runbook

## Purpose
Investigate queries whose execution time increases and contributes to database pressure.

## Signals
Inspect query latency percentiles, execution count, rows examined, rows returned, total database time, and query fingerprints. A query with a large increase in execution time or execution frequency can create substantial load even when individual requests appear normal.

## Investigation steps
1. Identify query fingerprints associated with the affected request path.
2. Compare latency and execution volume against a known healthy window.
3. Check whether the query plan, indexes, predicates, or data access pattern changed.
4. Correlate the first abnormal query observations with deployments and configuration changes.
5. Check for competing explanations such as traffic growth, lock contention, storage latency, or database infrastructure changes.

## Evidence standard
Do not treat a query fingerprint as the root cause by itself. Establish a temporal and causal relationship between the query behavior, database resource pressure, and application impact.
