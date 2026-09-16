# Application Error Rate Runbook

## Purpose
Investigate elevated request failures without assuming the application itself is the source of the problem.

## Initial checks
- Identify which endpoint or request class is affected.
- Compare error rate and latency with healthy services.
- Inspect dependency calls in traces.
- Correlate application errors with database, cache, network, and deployment telemetry.

## Dependency failures
A dependency can cause application requests to fail even when application processes remain healthy. Increasing dependency latency often appears before timeout or error-rate increases.

## Correlation
Use timestamps to determine whether dependency degradation precedes application failures. Check whether the same pattern occurs across unrelated endpoints and services.

## Escalation
If the affected dependency is a production database, use the database investigation runbooks before restarting application instances or changing application capacity.
