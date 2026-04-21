from __future__ import annotations

from src.producer_tools.self_check.gate_g5 import validate_hook_contract


def test_validate_hook_contract_pass_with_no_bypass_ledger_markers() -> None:
    pre_commit = "git diff --cached --name-only --diff-filter=ACMRD"
    pre_push = "oost-hook-ledger\npytest -q\ngit commit --amend --no-edit"
    commit_msg = "type(scope): summary"
    ci = "placeholder/mock markers detected\npytest -q\npyproject.toml"

    result = validate_hook_contract(
        pre_commit_text=pre_commit,
        pre_push_text=pre_push,
        commit_msg_text=commit_msg,
        ci_gate_text=ci,
    )

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_validate_hook_contract_fail_when_ledger_policy_missing() -> None:
    pre_commit = "git diff --cached --name-only --diff-filter=ACMRD"
    pre_push = "pytest -q"
    commit_msg = "type(scope): summary"
    ci = "placeholder/mock markers detected\npytest -q\npyproject.toml"

    result = validate_hook_contract(
        pre_commit_text=pre_commit,
        pre_push_text=pre_push,
        commit_msg_text=commit_msg,
        ci_gate_text=ci,
    )

    assert result["status"] == "fail"
    assert "no_bypass_ledger_policy" in result["failed_checks"]
