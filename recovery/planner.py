from recovery.models import RecoveryPlan, RecoveryStep
from graph.state import InvestigationState


# Conservative, hypothesis-driven recovery templates. These remain proposals only;
# the Safety Agent and human approval checkpoint control production changes.
_RECOVERY_TEMPLATES: dict[str, tuple[tuple[str, str, str, str, bool], ...]] = {
    "RSH1": (("inspect-wlm", "Inspect Redshift WLM queue state, query priorities, and concurrency limits.", "Identify queued workloads.", "low", False), ("adjust-wlm", "Prepare a reversible WLM queue or workload-priority adjustment for human review.", "Relieve queue contention with operator approval.", "medium", True), ("verify-wlm", "Verify queue wait time and query latency return toward baseline.", "Confirm queue recovery.", "low", False)),
    "RSH2": (("compare-query-plans", "Compare SQL revision, EXPLAIN plan, and Redshift query history.", "Validate query-plan regression.", "low", False), ("revert-sql", "Prepare a reviewed revert or correction of the SQL revision.", "Remove query regression with operator approval.", "medium", True), ("verify-query", "Verify scan volume, runtime, CPU, and errors return toward baseline.", "Confirm query recovery.", "low", False)),
    "RSH3": (("inspect-capacity", "Inspect Redshift compute utilization, concurrency, queueing, and workload demand.", "Determine compute headroom.", "low", False), ("plan-capacity", "Prepare a controlled capacity or concurrency adjustment for human review.", "Restore compute headroom.", "medium", True), ("verify-capacity", "Verify utilization, queue depth, and latency return toward baseline.", "Confirm capacity recovery.", "low", False)),
    "RSH4": (("inspect-load-errors", "Inspect Redshift load history, STL_LOAD_ERRORS, COPY options, manifests, and source files.", "Identify load failure.", "low", False), ("correct-load-input", "Prepare a validated correction to source files or COPY configuration for human review.", "Restore data loading.", "medium", True), ("verify-load", "Verify COPY errors, throughput, and job duration return toward baseline.", "Confirm pipeline health.", "low", False)),
    "RSH5": (("inspect-spectrum", "Inspect Spectrum history, external schemas, Glue metadata, and S3 access.", "Locate external-data failure.", "low", False), ("restore-external-access", "Prepare a reviewed correction to external schema, catalog, partition, or S3 access.", "Restore external-data access.", "medium", True), ("verify-spectrum", "Verify Spectrum scans and external-table queries succeed.", "Confirm recovery.", "low", False)),
    "RSH6": (("inspect-table-design", "Inspect SVV_TABLE_INFO, distribution skew, sort state, and statistics freshness.", "Validate table-design overhead.", "low", False), ("refresh-statistics", "Prepare ANALYZE or table-design correction for a maintenance window and human review.", "Improve optimizer information.", "medium", True), ("verify-table-performance", "Verify scan volume, runtime, and CPU return toward baseline.", "Confirm table recovery.", "low", False)),
    "RSH7": (("inspect-query-spill", "Inspect query history, execution plans, and spill metrics.", "Identify query spill.", "low", False), ("optimize-memory-workload", "Prepare a reviewed query or workload-allocation change to reduce spill.", "Reduce spill pressure.", "medium", True), ("verify-spill", "Verify spill volume, runtime, and timeouts return toward baseline.", "Confirm recovery.", "low", False)),
    "RSH8": (("inspect-authorizations", "Inspect Redshift IAM role, trust policy, S3 policy, and KMS key policy.", "Identify denied permission.", "low", False), ("restore-least-privilege", "Prepare the minimum required IAM, S3, or KMS permission correction for security review.", "Restore access safely.", "medium", True), ("verify-authorizations", "Verify the affected COPY, UNLOAD, or Spectrum operation succeeds.", "Confirm access recovery.", "low", False)),
    "RSH9": (("inspect-network-path", "Inspect endpoint reachability, security groups, routes, DNS, and VPC flow logs.", "Identify network failure.", "low", False), ("correct-network-rule", "Prepare a narrowly scoped network correction for human review.", "Restore connectivity safely.", "medium", True), ("verify-connectivity", "Verify client connections and query requests succeed.", "Confirm connectivity recovery.", "low", False)),
    "RSH10": (("inspect-cluster-events", "Inspect Redshift cluster events, node health, maintenance history, and service health.", "Establish cluster state.", "low", False), ("follow-cluster-runbook", "Prepare the documented Redshift recovery procedure for operator review.", "Restore service through the supported runbook.", "medium", True), ("verify-cluster", "Verify availability, query errors, and latency return toward baseline.", "Confirm cluster health.", "low", False)),
    "RSH11": (("inspect-data-share", "Inspect producer and consumer data-share state, grants, namespace, and authorization.", "Identify sharing failure.", "low", False), ("restore-share-access", "Prepare a reviewed correction to data-share grants or consumer authorization.", "Restore consumer access.", "medium", True), ("verify-data-share", "Verify the consumer can query the shared dataset.", "Confirm data-sharing recovery.", "low", False)),
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

    if adjudication is not None and adjudication.hypothesis_id == "RSH12":
        return RecoveryPlan(
            incident_id=incident_id,
            hypothesis_id="RSH12",
            confidence=float(adjudication.confidence),
            readiness="verification_required",
            rationale="Redshift evidence does not distinguish a specific failure mode. Collect targeted diagnostics before proposing remediation.",
            steps=(
                RecoveryStep(step_id="collect-redshift-diagnostics", action="Collect Redshift query history, WLM queue state, cluster events, CloudWatch metrics, and dependency authorization or network diagnostics.", purpose="Resolve the unknown or compound failure before selecting remediation.", risk="low", requires_approval=False),
                RecoveryStep(step_id="validate-candidate-causes", action="Compare collected evidence against Redshift hypotheses and document remaining gaps.", purpose="Establish a defensible trigger-to-impact chain.", risk="low", requires_approval=False),
            ),
        )

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
    # The adjudicator is the source of truth. Evidence-signal heuristics may
    # enrich a plan, but must never silently replace the adjudicated root cause.
    hypotheses = tuple(state.get("hypotheses", ()))
    selected_hypothesis = next(
        (item for item in hypotheses if item.hypothesis_id == adjudication.hypothesis_id),
        None,
    )
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
