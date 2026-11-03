"""Tests for the curated incident evaluation dataset."""

import json
from pathlib import Path


DATASET_PATH = Path(__file__).parents[2] / "evaluation" / "incident_cases.json"


def test_incident_dataset_has_thirty_five_unique_cases() -> None:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    assert len(cases) == 35
    incident_ids = [case["incident_id"] for case in cases]
    assert len(set(incident_ids)) == 35


def test_public_cases_have_source_provenance() -> None:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    public_cases = [case for case in cases if case["source_type"] == "github_public"]

    assert len(public_cases) == 14
    synthetic_cases = [case for case in cases if case["source_type"] == "synthetic_expansion"]
    assert len(synthetic_cases) == 15
    low_risk_cases = [case for case in cases if case.get("risk_level") == "LOW"]
    assert len(low_risk_cases) == 5
    assert all(case.get("severity") == "LOW" for case in low_risk_cases)
    for case in public_cases:
        assert case["source_url"].startswith("https://github.blog/")
        assert case["ground_truth_source"].startswith("GitHub Availability Report")


def test_every_case_has_evaluation_ground_truth() -> None:
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    required_fields = {
        "incident_id",
        "title",
        "source_type",
        "ground_truth_source",
        "source_url",
        "category",
        "expected_root_cause",
        "expected_trigger",
        "expected_affected_component",
        "expected_mitigation",
        "required_evidence",
        "expected_hypothesis_id",
    }

    for case in cases:
        assert required_fields <= case.keys()
        assert case["required_evidence"]
