# Deployment Validation

## Before rollout
Validate application behavior, database compatibility, query performance, and expected resource usage in a representative environment.

## After rollout
Monitor request latency and errors alongside dependency metrics. For database-backed services, monitor query execution time, query volume, CPU, locks, connection pressure, and storage latency.

## Regression detection
A regression may be visible as a new or unusually expensive query fingerprint, a change in query execution characteristics, or a resource increase that begins shortly after the rollout. Preserve telemetry around the change window so investigators can compare before and after behavior.
