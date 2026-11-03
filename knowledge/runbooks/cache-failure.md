# Redshift External Data Dependency Runbook

For Spectrum or external-table failures, inspect the Redshift external schema, Glue Data Catalog database/table/partition metadata, S3 object availability, file format and partition definitions, and the IAM role associated with the Redshift cluster. Correlate the dependency failure with the exact query ID and timestamp.

Do not classify a generic cache symptom as a Redshift incident. Only include a cache or intermediary dependency if evidence shows it directly affects the Redshift workload. If the Redshift relationship cannot be established, use RSH12 and request more diagnostics.
