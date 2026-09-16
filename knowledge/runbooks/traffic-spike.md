# Traffic Spike Investigation Runbook

## Purpose
Determine whether increased request volume explains an application or database incident.

## Checks
- Compare request volume with the normal baseline.
- Check whether traffic increased across all endpoints or only a subset.
- Compare request volume with database query execution rate.
- Check whether autoscaling and rate limiting behaved as expected.

## Interpretation
A traffic increase can raise database load, but increased load alone does not establish the cause of an incident. If traffic is stable while one query fingerprint becomes substantially more expensive, investigate query behavior and recent changes.
