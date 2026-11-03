# SentinelOps Redshift Domain Scope

## Product direction

SentinelOps is an evidence-led incident investigation and safe recovery planning system centered on **Amazon Redshift**.

Redshift is the primary system under investigation. AWS services that directly participate in a Redshift workload may be treated as contributing dependencies, but incidents must remain anchored to a Redshift workload, cluster, namespace, data warehouse, query, load, or integration.

This is a domain migration, not a rename of the existing generic database scenarios.

## In-scope AWS services

| Service | How it can contribute to a Redshift incident |
|---|---|
| Amazon Redshift | Query execution, WLM, concurrency, cluster health, capacity, storage, maintenance, data sharing |
| Amazon S3 | COPY/UNLOAD source or destination, external data, file format and object availability |
| AWS Glue Data Catalog | External schemas and Spectrum metadata |
| AWS IAM | Redshift, S3, Glue and role authorization |
| AWS KMS | Encryption key access for encrypted clusters or S3 data |
| Amazon VPC | Connectivity, security groups, routing and endpoints |
| Amazon CloudWatch | Metrics, alarms and diagnostic signals |

An AWS dependency is not an independent incident scope. For example, an S3 permission failure belongs in the dataset only when it causes a Redshift COPY, UNLOAD, or Spectrum workflow to fail.

## Candidate hypothesis taxonomy

These are competing explanations, not an exhaustive list and not mutually exclusive in every incident. The investigator must be able to retain an unknown/insufficient-evidence outcome rather than force an incident into a candidate.

| ID | Candidate hypothesis | Evidence that would make it more plausible |
|---|---|---|
| RSH1 | WLM queue contention or workload concurrency saturation | Queue wait time, queued queries, slot pressure, query priorities, WLM service-class evidence |
| RSH2 | Inefficient SQL or query-plan regression | Query runtime, execution plan changes, scan volume, joins, spills, query history and a correlated query change |
| RSH3 | Compute capacity or cluster sizing pressure | Sustained CPU/compute pressure, workload increase, resize history, concurrency scaling state and workload headroom |
| RSH4 | Data loading or COPY/UNLOAD bottleneck | Load errors, COPY history, S3 object availability, file format/manifest issues, throughput and load timing |
| RSH5 | Redshift Spectrum or external-data dependency failure | External schema, Spectrum query errors, Glue catalog lookups, S3 access, file format or partition metadata |
| RSH6 | Table design, data skew, statistics or maintenance regression | Distribution skew, sort-key effectiveness, stale statistics, unsorted rows, vacuum/analyze history and scan behavior |
| RSH7 | Storage pressure or query spill | Disk-based query steps, temporary storage pressure, spill volume, managed storage metrics and query execution details |
| RSH8 | IAM, KMS or authorization failure affecting Redshift workflows | AccessDenied events, role association, trust policy, KMS decrypt errors, S3/Glue permissions |
| RSH9 | VPC connectivity or client connection-path degradation | Connection failures, DNS/routing/security-group evidence, endpoint reachability and client-side timeouts |
| RSH10 | Redshift cluster health, maintenance or infrastructure event | Cluster status/events, maintenance window, node replacement, failover/recovery events and correlated query impact |
| RSH11 | Redshift data sharing or cross-warehouse consumer issue | Data-share authorization/state, consumer-side query failures, producer/consumer context and relevant events |
| RSH12 | Unknown or compound Redshift workload failure | Current evidence does not sufficiently distinguish candidates, or multiple independent causes are supported |

### Hypothesis semantics

- The top-ranked item is the **leading hypothesis**, not a confirmed root cause.
- Other candidates remain visible with their own evidence and contradictions.
- Confidence is an evidence-ranking score, not a calibrated probability.
- Missing evidence lowers confidence; it does not prove a candidate false.
- Contradictory evidence must reduce support.
- Historical knowledge, when added later, is bounded context and cannot override current incident evidence.
- The benchmark answer key is evaluation-only and must never be passed to agents.

## Evidence model

The Redshift simulator should emit evidence that resembles AWS operational telemetry while remaining explicitly synthetic. Candidate evidence sources include:

- CloudWatch metrics and alarms for Redshift namespaces and cluster/workload health.
- Redshift system views and logs, such as query, WLM, load, and query-monitoring history.
- Redshift cluster events and maintenance events.
- CloudTrail events for IAM, KMS, Glue, and relevant S3/API actions.
- S3 object and access evidence for COPY, UNLOAD, and Spectrum.
- VPC connectivity observations where the incident involves client connectivity.

Synthetic evidence must be labeled as simulated. It must not be represented as live AWS data.

## Recovery boundaries

Recovery recommendations must be Redshift-aware and conservative. Examples include inspecting query history, reviewing WLM configuration, validating S3/Glue/IAM access, checking table statistics and distribution, and preparing a controlled resize or workload change.

Potentially disruptive actions—query cancellation, WLM changes, resize, maintenance, permission changes, or workload cutover—must remain proposals subject to safety evaluation and human approval. SentinelOps must not claim that it executed AWS changes unless an explicitly configured integration actually performed them.

## Migration sequence

1. Stabilize the current investigation, persistence, safety, and human-approval workflow.
2. Replace the generic incident catalog with Redshift-centered synthetic incidents and AWS dependency scenarios.
3. Replace generic database hypotheses and causal evidence patterns with this Redshift taxonomy.
4. Replace recovery templates and runbooks with Redshift-specific, evidence-linked proposals.
5. Update benchmark labels, tests, UI copy, README, architecture, and demo instructions.
6. Validate that the workflow can return multiple candidates or insufficient evidence without forcing a diagnosis.

## Explicitly deferred

Automatic publication of approved/resolved incidents into a knowledge base and retrieval of those cases during hypothesis evaluation are deferred until the Redshift core workflow is stable.
