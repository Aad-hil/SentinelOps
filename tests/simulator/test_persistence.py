from unittest.mock import Mock

from simulator.__main__ import run_investigation


def test_run_investigation_persists_analysis_before_approval():
    repository = Mock()

    state = run_investigation("INC-002", repository=repository)

    assert state["investigation_status"] == "awaiting_human_approval"
    repository.initialize.assert_called_once()
    repository.save.assert_called_once()

    saved_memory = repository.save.call_args.args[0]
    assert saved_memory.incident_id == "INC-002"
    assert saved_memory.root_cause_hypothesis_id == "H1"
    assert saved_memory.root_cause_confidence == 1.0


def test_run_investigation_does_not_require_repository():
    state = run_investigation("INC-001")
    assert state["investigation_status"] == "complete"
