from __future__ import annotations


def test_gate_g2_fails_when_required_fields_missing() -> None:
    from src.producer_tools.self_check.gate_g2 import validate_failure_evidence

    result = validate_failure_evidence(
        {
            "symptom": "pytest assertion failed",
            "trigger_condition": "run pytest -q",
        }
    )

    assert result["status"] == "fail"
    assert "root_cause" in result["missing_fields"]
    assert "failure_command" in result["missing_fields"]


def test_gate_g2_passes_with_complete_failure_evidence() -> None:
    from src.producer_tools.self_check.gate_g2 import validate_failure_evidence

    result = validate_failure_evidence(
        {
            "symptom": "ModuleNotFoundError in test collection",
            "trigger_condition": "py -3.13 -m pytest -q tests/test_x.py",
            "root_cause": "missing module import path",
            "failure_command": "py -3.13 -m pytest -q tests/test_x.py",
            "observed_at": "2026-04-20T11:00:00+08:00",
        }
    )

    assert result["status"] == "pass"
    assert result["missing_fields"] == []
