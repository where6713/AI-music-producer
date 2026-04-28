from __future__ import annotations

from src.producer_tools.self_check.gate_g3 import validate_pass_evidence


def test_validate_pass_evidence_pass_with_local_ci_proof() -> None:
    result = validate_pass_evidence(
        {
            "local_command": "pytest -q",
            "local_result": "pass",
            "ci_result": "success",
            "ci_run_url": "https://github.com/where6713/AI-music-producer/actions/runs/1",
            "reproducible_commands": [
                "pytest -q",
                "python -m apps.cli.main gate-check --all",
            ],
            "local_output": "25 passed, 1 warning",
            "ci_output": "ci-quality-gates: success",
        }
    )

    assert result["status"] == "pass"
    assert result["missing_fields"] == []


def test_validate_pass_evidence_fail_when_ci_output_missing() -> None:
    result = validate_pass_evidence(
        {
            "local_command": "pytest -q",
            "local_result": "pass",
            "ci_result": "pass",
            "ci_run_url": "https://github.com/where6713/AI-music-producer/actions/runs/1",
            "reproducible_commands": ["pytest -q"],
            "local_output": "25 passed, 1 warning",
        }
    )

    assert result["status"] == "fail"
    assert "ci_output" in result["missing_fields"]


def test_validate_pass_evidence_fail_when_outputs_inconsistent() -> None:
    result = validate_pass_evidence(
        {
            "local_command": "pytest -q",
            "local_result": "pass",
            "ci_result": "pass",
            "ci_run_url": "https://github.com/where6713/AI-music-producer/actions/runs/1",
            "reproducible_commands": ["pytest -q"],
            "local_output": "25 passed, 1 warning",
            "ci_output": "ci-quality-gates: failed",
        }
    )

    assert result["status"] == "fail"
    assert "local_ci_output_consistency" in result["failed_checks"]
