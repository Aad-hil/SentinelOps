"""Tests for the Redshift-only deterministic simulator."""
from simulator.redshift import (
    build_all_redshift_incidents,
    build_redshift_incident,
    redshift_case_ids,
    build_redshift_evidence_bundle,
)


def test_all_redshift_incidents_are_deterministic_and_complete():
    first = build_all_redshift_incidents()
    second = build_all_redshift_incidents()
    assert len(first) == 12
    assert first == second
    assert tuple(item.incident.incident_id for item in first) == redshift_case_ids()
    for item in first:
        assert item.incident.service == "amazon-redshift"
        assert item.logs and item.metrics and item.deployments and item.traces
        assert item.ground_truth.root_cause


def test_redshift_evidence_bundle_excludes_ground_truth():
    evidence = build_redshift_evidence_bundle("RS-004")
    assert evidence.incident.incident_id == "RS-004"
    assert not hasattr(evidence, "ground_truth")


def test_legacy_incident_ids_are_not_supported():
    import pytest
    with pytest.raises(KeyError):
        build_redshift_incident("INC-002")
