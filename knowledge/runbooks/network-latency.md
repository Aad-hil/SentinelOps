# Redshift Client Connectivity Runbook

For Redshift connection failures, inspect endpoint and DNS resolution, VPC routing, security groups, network ACLs, subnet placement, VPC endpoints where applicable, and client-side connection errors. Correlate network evidence with Redshift connection/query history and cluster events.

Do not infer a VPC cause from query latency alone. Confirm that the connection path failed before query execution or that network telemetry supports the proposed mechanism. Use RSH9 when supported; otherwise retain RSH12.
