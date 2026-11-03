from agents.redshift_hypotheses import REDSHIFT_HYPOTHESES, get_redshift_hypothesis
from simulator.redshift import build_all_redshift_incidents, build_redshift_incident, redshift_case_ids
from simulator.evidence import build_evidence_bundle


def test_redshift_hypothesis_catalogue_has_twelve_unique_candidates():
    ids = [item.hypothesis_id for item in REDSHIFT_HYPOTHESES]
    assert len(ids) == 12
    assert len(set(ids)) == 12
    assert ids == [f"RSH{number}" for number in range(1, 13)]


def test_redshift_hypotheses_define_three_causal_stages():
    for item in REDSHIFT_HYPOTHESES:
        assert item.trigger_signals
        assert item.mechanism_signals
        assert item.impact_signals
        assert item.evidence_sources


def test_redshift_catalogue_lookup_is_explicit():
    assert get_redshift_hypothesis("RSH1").name == "WLM Queue Contention"


def test_redshift_simulator_builds_twelve_deterministic_cases():
    first = build_all_redshift_incidents()
    second = build_all_redshift_incidents()
    assert len(first) == 12
    assert redshift_case_ids() == tuple(f"RS-{number:03d}" for number in range(1, 13))
    assert [item.incident.incident_id for item in first] == list(redshift_case_ids())
    assert first == second


def test_redshift_scenarios_are_explicitly_scoped_to_amazon_redshift():
    for scenario in build_all_redshift_incidents():
        assert scenario.incident.service == "amazon-redshift"
        assert scenario.metrics
        assert scenario.logs
        assert scenario.deployments
        assert scenario.traces
        assert scenario.ground_truth.root_cause


def test_redshift_agent_evidence_does_not_expose_answer_key():
    scenario = build_redshift_incident("RS-001")
    evidence = build_evidence_bundle(
        incident=scenario.incident,
        logs=scenario.logs,
        metrics=scenario.metrics,
        deployments=scenario.deployments,
        traces=scenario.traces,
    )
    assert not hasattr(evidence, "ground_truth")
    assert evidence.incident.incident_id == "RS-001"



def test_redshift_hypothesis_engine_returns_ranked_redshift_candidates():
    from agents.deployment import run_deployment_agent
    from agents.root_cause import generate_hypotheses
    from agents.telemetry import run_telemetry_agent
    from simulator.redshift import build_redshift_evidence_bundle

    for incident_id in (f"RS-{number:03d}" for number in range(1, 13)):
        evidence = build_redshift_evidence_bundle(incident_id)
        state = {
            "incident_id": incident_id,
            "incident_summary": evidence.incident.description,
            "evidence": evidence,
        }
        state.update(run_telemetry_agent(state))
        state.update(run_deployment_agent(state))

        hypotheses = generate_hypotheses(state)
        hypothesis_ids = [item.hypothesis_id for item in hypotheses]
        confidences = [item.confidence for item in hypotheses]

        # The engine must return the Redshift catalogue, not generic H1-H12
        # candidates, and must provide a deterministic confidence ranking.
        assert len(hypotheses) == 12, incident_id
        assert set(hypothesis_ids) == {
            f"RSH{number}" for number in range(1, 13)
        }, (incident_id, hypothesis_ids)
        assert confidences == sorted(confidences, reverse=True), (
            incident_id,
            confidences,
        )
        assert all(0.0 <= confidence <= 1.0 for confidence in confidences)


def test_redshift_unknown_case_recovery_is_diagnostic_only():
    from agents.root_cause import Hypothesis
    from recovery.planner import build_recovery_plan
    from agents.adjudication import Adjudication
    from simulator.redshift import build_redshift_evidence_bundle

    evidence = build_redshift_evidence_bundle("RS-012")
    adjudication = Adjudication(
        hypothesis_id="RSH12",
        display_name="Unknown or Compound Redshift Workload Failure",
        statement="Available evidence is insufficient or supports multiple interacting causes.",
        brief_explanation="Insufficient evidence.",
        full_explanation="Insufficient evidence.",
        rationale="No specific cause is established.",
        temporal_support=False,
        causal_support=False,
        recovery_support=False,
        alternative_gaps=("specific trigger",),
        confidence=0.3,
    )
    plan = build_recovery_plan({
        "incident_id": "RS-012",
        "evidence": evidence,
        "adjudication": adjudication,
        "hypotheses": [Hypothesis(
            hypothesis_id="RSH12",
            display_name="Unknown",
            statement="Unknown",
            supporting_evidence=(),
            contradicting_evidence=(),
            confidence=0.3,
        )],
    })
    assert plan.readiness == "verification_required"
    assert all(step.risk == "low" and not step.requires_approval for step in plan.steps)
