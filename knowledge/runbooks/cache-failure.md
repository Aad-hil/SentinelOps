# Cache Failure Investigation Runbook

A cache failure can increase backend work and indirectly increase database load. Check cache hit rate, eviction rate, backend request volume, and application errors.

A cache-related hypothesis should be supported by a measurable change in cache behavior and a corresponding increase in backend workload. Stable cache indicators make this explanation less likely for a database saturation incident.
