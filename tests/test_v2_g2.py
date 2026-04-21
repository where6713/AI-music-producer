from __future__ import annotations

from src.producer_tools.self_check.gate_g2 import validate_failure_evidence


def test_validate_failure_evidence_pass_with_failure_snapshot() -> None:
    result = validate_failure_evidence(
        {
            "symptom": "scope-check g1 returns commit_scope_g1",
            "trigger_condition": "run scope-check g1 on non-g1 commit",
            "root_cause": "HEAD commit scope is g0, not g1",
            "failure_command": "python -m apps.cli.main scope-check g1",
            "failure_output": "G1 SCOPE-CHECK FAIL\nfailed_checks: commit_scope_g1",
        }
    )

    assert result["status"] == "pass"
    assert result["missing_fields"] == []


def test_validate_failure_evidence_fail_when_failure_output_missing() -> None:
    result = validate_failure_evidence(
        {
            "symptom": "scope-check g1 returns commit_scope_g1",
            "trigger_condition": "run scope-check g1 on non-g1 commit",
            "root_cause": "HEAD commit scope is g0, not g1",
            "failure_command": "python -m apps.cli.main scope-check g1",
        }
    )

    assert result["status"] == "fail"
    assert "failure_output" in result["missing_fields"]
