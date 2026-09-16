# Database Topology

Production database workloads commonly use a primary node for writes and one or more replicas for read workloads. The primary can become a bottleneck when write traffic, expensive queries, lock contention, or inefficient execution plans consume available resources.

## Investigation notes
Check primary-specific CPU, query load, queue depth, storage latency, and lock waits. Compare replicas and other database nodes when useful. A primary-only resource spike can narrow the investigation toward write-path workload or primary-specific conditions.

Database saturation can propagate upward as increased dependency latency, request timeouts, and application errors.
