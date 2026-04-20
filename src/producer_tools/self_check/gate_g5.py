from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_hook_contract(
    *,
    pre_commit_text: str,
    pre_push_text: str,
    commit_msg_text: str,
    ci_gate_text: str,
) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    if "--diff-filter=ACMRD" not in pre_commit_text:
        failed_checks.append("pre_commit_diff_filter")

    lowered_hooks = (pre_commit_text + "\n" + pre_push_text).lower()
    has_no_verify_execution = (
        "git commit --no-verify" in lowered_hooks
        or "git push --no-verify" in lowered_hooks
        or "--no-verify\n" in lowered_hooks
    )
    if has_no_verify_execution:
        failed_checks.append("no_verify_policy")

    if "type(scope): summary" not in commit_msg_text and "^(feat|fix|docs|refactor|test|chore|build|ci|perf|revert)" not in commit_msg_text:
        failed_checks.append("commit_message_policy")

    marker_mock = "mock" + "_data"
    marker_lorem = "Lorem" + " ipsum"
    has_placeholder_scan = marker_mock in ci_gate_text and marker_lorem in ci_gate_text
    if not has_placeholder_scan:
        failed_checks.append("ci_placeholder_scan")

    has_show_me_output = "SHOW-ME-OUTPUT" in ci_gate_text
    if not has_show_me_output:
        failed_checks.append("ci_show_me_output")

    has_pytest_gate = "pytest -q" in pre_push_text and "pytest -q" in ci_gate_text
    if not has_pytest_gate:
        failed_checks.append("hook_ci_test_parity")

    status = "pass" if not failed_checks else "fail"
    if status == "fail":
        warnings.append("Hook/CI contract mismatch detected")

    return {
        "status": status,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def check_gate_g5(workspace_root: Path) -> dict[str, Any]:
    hooks_dir = workspace_root / "tools" / "githooks"
    scripts_dir = workspace_root / "tools" / "scripts"

    pre_commit_path = hooks_dir / "pre-commit"
    pre_push_path = hooks_dir / "pre-push"
    commit_msg_path = hooks_dir / "commit-msg"
    ci_gate_path = scripts_dir / "run_quality_gates_ci.sh"

    missing_files = [
        str(path.relative_to(workspace_root))
        for path in [pre_commit_path, pre_push_path, commit_msg_path, ci_gate_path]
        if not path.exists()
    ]
    if missing_files:
        return {
            "status": "fail",
            "failed_checks": ["required_files"],
            "warnings": [f"Missing required files: {', '.join(missing_files)}"],
            "missing_files": missing_files,
        }

    pre_commit_text = pre_commit_path.read_text(encoding="utf-8", errors="ignore")
    pre_push_text = pre_push_path.read_text(encoding="utf-8", errors="ignore")
    commit_msg_text = commit_msg_path.read_text(encoding="utf-8", errors="ignore")
    ci_gate_text = ci_gate_path.read_text(encoding="utf-8", errors="ignore")

    result = validate_hook_contract(
        pre_commit_text=pre_commit_text,
        pre_push_text=pre_push_text,
        commit_msg_text=commit_msg_text,
        ci_gate_text=ci_gate_text,
    )
    result["missing_files"] = []
    return result
