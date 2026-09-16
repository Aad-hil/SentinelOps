# Incident Pattern: Database Connection Pool Exhaustion

This historical training scenario describes an application whose database connection pool becomes exhausted. Typical signals include increasing connection acquisition time, pool utilization approaching its configured maximum, growing database connection wait queues, and application request failures.

Investigators should compare connection-pool metrics with database latency and recent configuration or application changes. Increasing pool capacity may help when the pool is undersized, but changing capacity without understanding the underlying workload can move pressure to the database.
