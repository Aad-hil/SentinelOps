# Deployment Rollback Runbook

## Purpose
Safely restore service behavior when a recent deployment is strongly correlated with production degradation.

## Preconditions
- Confirm the affected service and deployment version.
- Capture relevant logs, metrics, traces, and deployment metadata before rollback when possible.
- Check whether rollback is supported and whether database or schema changes make rollback unsafe.
- Determine whether approval is required by the production change policy.

## Procedure
1. Confirm the suspected deployment window.
2. Compare the current version with the previous known-good version.
3. Record the reason and evidence supporting rollback.
4. Execute the approved rollback procedure.
5. Monitor request errors, latency, dependency health, and database load.

## Verification
A rollback is not considered successful until affected service indicators return toward the pre-incident baseline and the suspected failure signal stops worsening.
