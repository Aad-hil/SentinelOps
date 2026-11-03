"""Tests for the Redshift-only evaluation dataset."""
import json
from pathlib import Path

DATASET_PATH = Path(__file__).parents[2] / "evaluation" / "incident_cases.json"


def test_dataset_contains_only_twelve_redshift_cases():
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    assert len(cases) == 12
    assert [case["incident_id"] for case in cases] == [f"RS-{n:03d}" for n in range(1, 13)]
    assert [case["expected_hypothesis_id"] for case in cases] == [f"RSH{n}" for n in range(1, 13)]


def test_all_dataset_cases_are_explicitly_synthetic_redshift_cases():
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    for case in cases:
        assert case["source_type"] == "synthetic"
        assert case["ground_truth_source"] == "simulator/redshift.py"
        assert case["source_url"] is None
        assert "not live AWS telemetry" in case["public_facts_note"]
