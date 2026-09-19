from recovery.models import RecoveryPlan, RecoveryStep
from graph.state import InvestigationState


# Conservative, hypothesis-driven recovery templates. These remain proposals only;
# the Safety Agent and human approval checkpoint control production changes.
_RECOVERY_TEMPLATES: dict[str, tuple[tuple[str, str, str, str, bool], ...]] = {
    "H1": (
        ("identify-query", "Identify and isolate the database query associated with the validated deployment change.", "Confirm the causal query before changing production state.", "low", False),
        ("rollback-deployment", "Roll back the deployment that introduced the database-impacting query.", "Remove the suspected trigger with a reversible deployment action.", "medium", True),
        ("verify-database-recovery", "Verify database CPU, query latency, error rate, and service health return toward baseline.", "Confirm that rollback restored service health.", "low", False),
    ),
    "H2": (
        ("throttle-load", "Throttle or reduce excessive request load while protecting database capacity.", "Reduce pressure on the overloaded service or database.", "medium", True),
        ("verify-load-recovery", "Verify request rate, database utilization, latency, and errors return toward baseline.", "Confirm that load reduction restored service health.", "low", False),
    ),
    "H3": (
        ("isolate-dependency", "Isolate the affected downstream dependency or network path and validate connectivity.", "Confirm the dependency path responsible for failures.", "low", False),
        ("restore-dependency-path", "Apply the documented reversible dependency or network mitigation after human review.", "Restore the affected request path without autonomous production changes.", "medium", True),
        ("verify-dependency-recovery", "Verify downstream latency, request failures, and service health return toward baseline.", "Confirm dependency recovery.", "low", False),
    ),
    "H4": (
        ("protect-connection-capacity", "Reduce connection pressure and prepare a reversible connection-capacity mitigation.", "Prevent further connection exhaustion.", "medium", True),
        ("verify-connections", "Verify connection utilization, wait time, latency, and request failures return toward baseline.", "Confirm connection capacity recovered.", "low", False),
    ),
    "H5": (
        ("disable-query-change", "Disable or roll back the problematic database query change after human review.", "Remove the suspected query regression causing contention.", "medium", True),
        ("verify-query-recovery", "Verify lock contention, query latency, database resource usage, and errors return toward baseline.", "Confirm the query change was the source of pressure.", "low", False),
        ("refactor-query", "Refactor and validate the problematic query before the permanent production rollout.", "Prevent recurrence from the query regression.", "medium", True),
    ),
    "H6": (
        ("pause-migration", "Pause or safely complete the active schema migration before further workload changes.", "Remove migration overlap from the contention window.", "medium", True),
        ("verify-migration-recovery", "Verify connection utilization, database resource contention, latency, and errors return toward baseline.", "Confirm migration-related pressure has cleared.", "low", False),
        ("stabilize-migration", "Revert the schema-change tooling regression to a stable version before the next migration attempt.", "Prevent recurrence during future schema changes.", "medium", True),
    ),
    "H7": (
        ("stabilize-primary", "Stabilize the database primary and failover path using the documented recovery procedure.", "Restore a stable primary without autonomous destructive actions.", "medium", True),
        ("verify-failover", "Verify primary health, failover stability, and request error rate return toward baseline.", "Confirm the failover path is stable.", "low", False),
        ("correct-database-configuration", "Correct and validate the affected database version or cluster configuration before rollout.", "Prevent repeated primary crashes.", "medium", True),
    ),
    "H8": (
        ("revert-write-path", "Revert writes to the last known-good database cluster or configuration after human review.", "Restore successful database writes while preserving operator control.", "medium", True),
        ("correct-permissions", "Correct and validate the missing database permissions before retrying the migration.", "Restore the required insert/write authorization safely.", "medium", True),
        ("verify-write-recovery", "Verify insert/write success, latency, and request error rate return toward baseline.", "Confirm the permission regression is resolved.", "low", False),
    ),
    "H9": (
        ("block-expensive-pattern", "Block or reduce the source of the expensive database write/query pattern after human review.", "Stop the workload causing excessive database resource consumption.", "medium", True),
        ("verify-write-recovery", "Verify database write latency, query CPU, dependent latency, and timeouts return toward baseline.", "Confirm expensive writes are no longer degrading the service.", "low", False),
        ("correct-endpoint-pattern", "Correct similar endpoint or API data-shape patterns before permanent rollout.", "Prevent recurrence of expensive database transactions.", "medium", True),
    ),
    "H10": (
        ("reduce-token-load", "Prevent excessive token-request load from overloading the database and prepare request throttling.", "Reduce query amplification against the database replicas.", "medium", True),
        ("verify-replication", "Verify replication lag, query latency, and replica freshness return toward baseline.", "Confirm replicas have recovered sufficiently for dependent requests.", "low", False),
        ("improve-query-behavior", "Improve and validate the query behavior responsible for replication pressure.", "Prevent recurrence of query amplification.", "medium", True),
    ),
    "H11": (
        ("rollback-upgrade", "Roll back the data-store or infrastructure upgrade to the previous stable version after human review.", "Remove the upgrade-associated resource contention.", "medium", True),
        ("verify-upgrade-recovery", "Verify resource contention, query latency, timeout rate, and dependent service health return toward baseline.", "Confirm the rollback restored service health.", "low", False),
    ),
    "H12": (
        ("fix-inefficient-query", "Fix or disable the inefficient database query after human review.", "Remove the database operation driving background workload pressure.", "medium", True),
        ("protect-api-load", "Apply endpoint rate limits or request throttling to prevent query amplification.", "Limit the workload that can recreate the backlog.", "medium", True),
        ("verify-queue-recovery", "Verify background-job and webhook queue depth, query latency, and request health return toward baseline.", "Confirm backlog recovery.", "low", False),
    ),
}


def _template_steps(
    hypothesis_id: str,
    evidence: tuple[str, ...] = (),
) -> tuple[RecoveryStep, ...]:
    """Instantiate a hypothesis template and preserve its causal evidence sources."""
    return tuple(
        RecoveryStep(
            step_id=step_id,
            action=action,
            purpose=purpose,
            risk=risk,
            requires_approval=requires_approval,
            evidence=evidence,
        )
        for step_id, action, purpose, risk, requires_approval
        in _RECOVERY_TEMPLATES.get(hypothesis_id, ())
    )


def build_recovery_plan(state: InvestigationState) -> RecoveryPlan:
    """Build a conservative recovery recommendation from adjudication and critique."""
    adjudication = state.get("adjudication")
    critique = state.get("critique")
    incident_id = state.get("incident_id") or state["evidence"].incident.incident_id

    if adjudication is None:
        return RecoveryPlan(
            incident_id=incident_id,
            hypothesis_id=None,
            confidence=0.0,
            readiness="blocked",
            rationale="No adjudicated root-cause hypothesis is available for recovery planning.",
            steps=(
                RecoveryStep(
                    step_id="verify-root-cause",
                    action="Collect additional evidence before changing production state.",
                    purpose="Avoid remediation based on an unvalidated hypothesis.",
                    risk="low",
                    requires_approval=False,
                ),
            ),
        )

    confidence = float(adjudication.confidence)
    hypothesis_id = adjudication.hypothesis_id
    gaps = tuple(adjudication.alternative_gaps)
    missing = tuple(getattr(critique, "missing_evidence", ())) if critique else ()
    unresolved = tuple(dict.fromkeys((*gaps, *missing)))

    if not (
        adjudication.temporal_support
        and adjudication.causal_support
        and adjudication.recovery_support
    ):
        gap_text = "; ".join(unresolved) or "causal and recovery evidence"
        hypotheses = tuple(state.get("hypotheses", ()))
        leading = next(
            (hypothesis for hypothesis in hypotheses if hypothesis.hypothesis_id == hypothesis_id),
            None,
        )
        causal_evidence = tuple(leading.causal_evidence) if leading else ()
        template_steps = _template_steps(hypothesis_id, causal_evidence)
        if template_steps and leading and (adjudication.causal_support or leading.causal_score >= 0.333 or leading.supporting_evidence):
            prepared_steps = tuple(
                RecoveryStep(
                    step_id=f"prepare-{step.step_id}",
                    action=f"Prepare and validate this candidate action for human review; do not execute automatically: {step.action}",
                    purpose=step.purpose,
                    risk=step.risk,
                    requires_approval=step.requires_approval,
                    evidence=step.evidence,
                )
                for step in template_steps
            )
            steps = (
                RecoveryStep(
                    step_id="collect-missing-evidence",
                    action="Collect the missing causal, temporal, and recovery evidence.",
                    purpose="Validate the leading hypothesis before remediation.",
                    risk="low",
                    requires_approval=False,
                    evidence=unresolved,
                ),
                *prepared_steps,
            )
        else:
            steps = (
                RecoveryStep(
                    step_id="collect-missing-evidence",
                    action="Collect the missing causal, temporal, and recovery evidence.",
                    purpose="Validate the leading hypothesis before remediation.",
                    risk="low",
                    requires_approval=False,
                    evidence=unresolved,
                ),
                RecoveryStep(
                    step_id="prepare-mitigation",
                    action="Prepare a reversible mitigation for human review; do not execute it automatically.",
                    purpose="Reduce incident impact while preserving operator control.",
                    risk="medium",
                    requires_approval=True,
                ),
            )
        return RecoveryPlan(
            incident_id=incident_id,
            hypothesis_id=hypothesis_id,
            confidence=confidence,
            readiness="verification_required",
            rationale=(
                f"Recovery action is not ready for production execution because the investigation "
                f"has unresolved evidence gaps: {gap_text}. A hypothesis-specific mitigation is "
                "prepared for validation where causal evidence is sufficiently specific."
            ),
            steps=steps,
        )

    hypotheses = tuple(state.get("hypotheses", ()))
    leading = next(
        (hypothesis for hypothesis in hypotheses if hypothesis.hypothesis_id == hypothesis_id),
        None,
    )
    causal_evidence = tuple(leading.causal_evidence) if leading else ()
    steps = _template_steps(hypothesis_id, causal_evidence)
    if not steps:
        steps = (
            RecoveryStep(
                step_id="mitigate",
                action="Apply the documented mitigation associated with the validated root cause.",
                purpose="Reduce ongoing customer impact.",
                risk="medium",
                requires_approval=True,
            ),
            RecoveryStep(
                step_id="verify-recovery",
                action="Verify error rate, latency, and service health return toward baseline.",
                purpose="Confirm that mitigation restored service health.",
                risk="low",
                requires_approval=False,
            ),
            RecoveryStep(
                step_id="permanent-fix",
                action="Document and validate the permanent fix before production rollout.",
                purpose="Prevent recurrence after immediate recovery.",
                risk="medium",
                requires_approval=True,
            ),
        )
    return RecoveryPlan(
        incident_id=incident_id,
        hypothesis_id=hypothesis_id,
        confidence=confidence,
        readiness="ready_for_review",
        rationale="The leading hypothesis has temporal, causal, and recovery support; proposed actions still require human review where production state may change.",
        steps=steps,
    )
