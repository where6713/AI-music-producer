from __future__ import annotations


def test_gate_g3_fails_on_inconsistent_local_and_ci_status() -> None:
    from src.producer_tools.self_check.gate_g3 import validate_pass_evidence

    result = validate_pass_evidence(
        {
            "local_command": "py -3.13 -m pytest -q",
            "local_result": "pass",
            "ci_result": "fail",
            "ci_run_url": "https://github.com/org/repo/actions/runs/1/job/2",
            "reproducible_commands": [
                "py -3.13 -m pytest -q",
                "bash tools/scripts/run_quality_gates_ci.sh",
            ],
        }
    )

    assert result["status"] == "fail"
    assert result["consistent"] is False
    assert result["missing_fields"] == []


def test_gate_g3_passes_with_consistent_and_reproducible_evidence() -> None:
    from src.producer_tools.self_check.gate_g3 import validate_pass_evidence

    result = validate_pass_evidence(
        {
            "local_command": "py -3.13 -m pytest -q",
            "local_result": "pass",
            "ci_result": "success",
            "ci_run_url": "https://github.com/org/repo/actions/runs/100/job/200",
            "reproducible_commands": [
                "py -3.13 -m pytest -q",
                "bash tools/scripts/run_quality_gates_ci.sh",
            ],
        }
    )

    assert result["status"] == "pass"
    assert result["consistent"] is True
    assert result["missing_fields"] == []
