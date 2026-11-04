# Redshift Workload Topology

The active SentinelOps domain is Amazon Redshift. Model the workload path as client or application → VPC/network path → Redshift endpoint/namespace → WLM queue → query execution → local or external data sources. COPY and UNLOAD may depend on S3; Spectrum may depend on S3 and Glue Data Catalog; encrypted resources may depend on IAM and KMS.

Use workload identity, query IDs, timestamps, and cluster/namespace context to connect evidence. This document is operational guidance, not a representation of a live deployment topology.
