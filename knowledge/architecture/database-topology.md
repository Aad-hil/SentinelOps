# Amazon Redshift Workload Architecture

SentinelOps investigates Amazon Redshift workloads. Treat S3, Glue Data Catalog, IAM, KMS, VPC, and CloudWatch as dependencies only when evidence connects them to a Redshift query, load, unload, Spectrum, data-share, or client-connection failure.

## Investigation map

- Workload management: WLM queues, service classes, priorities, concurrency, queue wait.
- Query execution: query history, query plans, scan volume, runtime, spill and execution steps.
- Cluster capacity and health: compute utilization, concurrency scaling, resize history, cluster events and maintenance.
- Data movement: COPY/UNLOAD history, S3 objects, manifests, formats and throughput.
- External data: Spectrum, external schemas, Glue catalog, partitions and S3 access.
- Table health: distribution skew, sort state, statistics freshness and maintenance.
- Security and connectivity: IAM role/trust/policies, KMS access, VPC routes, security groups, DNS and endpoints.

Correlate evidence by timestamp and workload identity. A dependency symptom alone does not establish the Redshift root cause. All repository simulator evidence is synthetic, not live AWS telemetry.
