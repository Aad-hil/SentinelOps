# Web Application Service Model

The web application handles incoming requests and depends on shared backend services. Request success and latency therefore depend on both application processing and downstream dependency health.

For incident investigation, application-level errors should be correlated with dependency telemetry and distributed traces. A healthy application process does not rule out a downstream database problem.
