# Production Deployment Process

Production deployments should record the service, new version, previous version, deployment timestamp, change summary, and rollout status.

## Investigation use
When an incident follows a deployment, compare the deployment timestamp with the first abnormal telemetry. Inspect the change summary and identify components that could plausibly affect the failing request path.

Deployment timing is correlation evidence, not proof of causation. Combine it with telemetry and traces showing a corresponding behavior change.
