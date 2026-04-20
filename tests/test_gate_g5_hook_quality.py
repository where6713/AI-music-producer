from __future__ import annotations

from pathlib import Path


def test_gate_g5_fails_when_precommit_missing_delete_filter() -> None:
    from src.producer_tools.self_check.gate_g5 import validate_hook_contract

    result = validate_hook_contract(
        pre_commit_text='staged_files="$(git diff --cached --name-only --diff-filter=ACMR)"',
        pre_push_text='echo "[pre-push]"',
        commit_msg_text='grep -Eq "^(feat|fix)\\([a-z]+\\): .+"',
        ci_gate_text='grep -Ev "^(README\\.md)$"',
    )

    assert result["status"] == "fail"
    assert "pre_commit_diff_filter" in result["failed_checks"]


def test_gate_g5_passes_current_repo_contract() -> None:
    from src.producer_tools.self_check.gate_g5 import check_gate_g5

    result = check_gate_g5(Path.cwd())

    assert result["status"] == "pass"
    assert result["failed_checks"] == []
