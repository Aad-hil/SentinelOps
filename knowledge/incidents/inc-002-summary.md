# Historical Incident Pattern: Primary Database Saturation

This document is a training reference for a class of production incidents in which a primary database becomes saturated and application requests begin failing.

Useful investigation signals include primary CPU, query latency, query execution volume, rows examined, lock or queue pressure, request latency, and error rate. When the degradation follows a deployment, compare the workload before and after the change and determine whether a specific query or request path changed behavior.

Do not use this document as proof of the cause of any particular incident. It describes an investigation pattern and should be combined with incident-specific telemetry.
