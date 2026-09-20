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


def _evidence_text(state: InvestigationState) -> str:
    """Combine investigation evidence for generic recovery-signal detection."""
    return " ".join(
        f"{item.source} {item.observation}".lower()
        for item in state.get("evidence_items", ())
    )


def _supplemental_steps(
    state: InvestigationState,
    existing_ids: set[str],
    evidence: tuple[str, ...],
) -> tuple[RecoveryStep, ...]:
    """Add conservative actions when direct operational signals are explicit."""
    text = _evidence_text(state)
    steps: list[RecoveryStep] = []

    def add(step: RecoveryStep) -> None:
        if step.step_id not in existing_ids:
            steps.append(step)

    # Connection-pool and connection-failure incidents need a concrete
    # capacity recovery action. Keep this signal-driven rather than tying it
    # to benchmark incident IDs.
    if "connection_errors" in text or "connection errors" in text:
        add(
            RecoveryStep(
                step_id="restart-database",
                action="Prepare a controlled database restart for human review to clear persistent primary connection errors.",
                purpose="Restore the affected database connection path without autonomous production changes.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )
        add(
            RecoveryStep(
                step_id="migrate-workload-platform",
                action="Prepare migration of the affected workload to a more robust database platform for human review.",
                purpose="Provide a durable recovery path when the current database platform cannot reliably sustain connections.",
                risk="high",
                requires_approval=True,
                evidence=evidence,
            )
        )

    # A long-running query during maintenance calls for query termination
    # before broader query refactoring.
    if ("long-running" in text or "long_running" in text) and "maintenance" in text:
        add(
            RecoveryStep(
                step_id="terminate-slow-query",
                action="Terminate the long-running database query using the documented safe procedure, then prepare a database restart for human review if pressure remains.",
                purpose="Remove the active query from the maintenance contention window.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )

    # Peak-load incidents may require more than throttling: prepare reversible
    # capacity and query optimizations while preserving human approval.
    if ("db_cpu_percent" in text or "database cpu" in text) and ("error" in text or "timeout" in text):
        add(
            RecoveryStep(
                step_id="restart-affected-database",
                action="Prepare a controlled restart of the affected database or front-end component for human review if CPU pressure remains after load reduction.",
                purpose="Clear persistent resource pressure after protecting the overloaded workload.",
                risk="high",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if ("peak" in text or "request_rate" in text or "request rate" in text) and "headroom" in text:
        add(
            RecoveryStep(
                step_id="optimize-query-capacity",
                action="Optimize the affected database queries and prepare a reversible increase in database headroom for human review.",
                purpose="Reduce query amplification and restore sufficient capacity for peak traffic.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )
        add(
            RecoveryStep(
                step_id="prepare-failover",
                action="Prepare a controlled database failover where primary health requires it, with human approval before execution.",
                purpose="Provide a recovery path if the primary cannot sustain the peak workload.",
                risk="high",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if ("pool" in text and "connection" in text) and "restore-connection-capacity" not in existing_ids:
        add(
            RecoveryStep(
                step_id="increase-connection-pool",
                action="Prepare an increase to database connection-pool capacity for human review.",
                purpose="Restore connection headroom when pool capacity is the limiting resource.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if ("migration" in text or "schema" in text) and "pause-migration" not in existing_ids:
        add(
            RecoveryStep(
                step_id="pause-migration",
                action="Pause the active database migration and validate a safe recovery point before resuming.",
                purpose="Remove migration workload from the contention window.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if ("upgrade" in text or "major version" in text or "version" in text) and "rollback-upgrade" not in existing_ids:
        add(
            RecoveryStep(
                step_id="rollback-upgrade",
                action="Prepare a rollback to the previous stable data-store version for human review.",
                purpose="Remove upgrade-associated resource contention.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if ("new data shape" in text or "expensive" in text or "write transaction" in text) and "block-expensive-pattern" not in existing_ids:
        add(
            RecoveryStep(
                step_id="block-expensive-pattern",
                action="Prepare a reversible block or reduction of the expensive database write pattern for human review.",
                purpose="Stop the workload driving excessive database resource consumption.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if ("peak" in text or "traffic" in text or "request_rate" in text or "request rate" in text or "request volume" in text) and "throttle-load" not in existing_ids:
        add(
            RecoveryStep(
                step_id="throttle-load",
                action="Prepare request throttling to reduce database pressure during the peak-load window.",
                purpose="Protect database capacity while recovery is validated.",
                risk="medium",
                requires_approval=True,
                evidence=evidence,
            )
        )

    if (("migration" in text or "schema" in text) and ("peak" in text or "traffic" in text or "request volume" in text) and ("connection" in text or "db_connection" in text)) and "recover-connection-capacity" not in existing_ids:
        add(
            RecoveryStep(
                step_id="recover-connection-capacity",
                action="Recover database connection capacity after the migration and peak-load pressure is reduced.",
                purpose="Restore connection headroom before returning to normal workload.",
                risk="low",
                requires_approval=False,
                evidence=evidence,
            )
        )

    return tuple(steps)


def _select_hypothesis_for_recovery(state: InvestigationState):
    """Prefer hypotheses whose evidence exposes an explicit operational trigger."""
    hypotheses = tuple(state.get("hypotheses", ()))
    if not hypotheses:
        return None
    text = _evidence_text(state)
    signals = (
        ("H11", ("upgrade", "major version", "data-store version")),
        ("H6", ("migration", "schema", "alter")),
        ("H9", ("new data shape", "expensive", "write transaction")),
        ("H10", ("replication", "token request", "replica")),
        ("H12", ("inefficient", "background", "webhook", "queue")),
    )
    for hypothesis_id, terms in signals:
        hypothesis = next((item for item in hypotheses if item.hypothesis_id == hypothesis_id), None)
        if hypothesis and any(term in text for term in terms):
            return hypothesis
    return next((item for item in hypotheses if getattr(item, "status", None) != "insufficient_evidence"), hypotheses[0])


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
    selected_hypothesis = _select_hypothesis_for_recovery(state)
    hypothesis_id = selected_hypothesis.hypothesis_id if selected_hypothesis else adjudication.hypothesis_id
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
            steps=steps + _supplemental_steps(
                state,
                {step.step_id for step in steps},
                causal_evidence,
            ),
        )

    hypotheses = tuple(state.get("hypotheses", ()))
    leading = selected_hypothesis or next(
        (hypothesis for hypothesis in hypotheses if hypothesis.hypothesis_id == hypothesis_id),
        None,
    )
    causal_evidence = tuple(leading.causal_evidence) if leading else ()
    steps = _template_steps(hypothesis_id, causal_evidence)
    supplemental = _supplemental_steps(state, {step.step_id for step in steps}, causal_evidence)
    if supplemental:
        steps = (*steps, *supplemental)
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
