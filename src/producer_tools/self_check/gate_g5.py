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

    if "--diff-filter=ACMRD" not in pre_commit_text:
        failed_checks.append("pre_commit_diff_filter")

    lowered = (pre_commit_text + "\n" + pre_push_text).lower()
    if "git commit --no-verify" in lowered or "git push --no-verify" in lowered:
        failed_checks.append("no_verify_policy")

    if "type(scope): summary" not in commit_msg_text:
        failed_checks.append("commit_message_policy")

    if "placeholder/mock markers detected" not in ci_gate_text:
        failed_checks.append("ci_placeholder_scan")

    if "pytest -q" not in pre_push_text or "pytest -q" not in ci_gate_text:
        failed_checks.append("hook_ci_test_parity")

    if "apps.cli.main pm-audit" not in pre_push_text or "apps.cli.main pm-audit" not in ci_gate_text:
        failed_checks.append("hook_ci_pm_audit_parity")

    output_contract_markers = ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"]
    if not all(marker in pre_push_text for marker in output_contract_markers):
        failed_checks.append("hook_output_contract_check")
    if not all(marker in ci_gate_text for marker in output_contract_markers):
        failed_checks.append("ci_output_contract_check")

    has_ledger_policy = (
        "oost-hook-ledger" in pre_push_text
        and "git commit --amend --no-edit" in pre_push_text
    )
    if not has_ledger_policy:
        failed_checks.append("no_bypass_ledger_policy")

    has_pyproject_marker = (
        "pyproject.toml" in pre_commit_text
        or "pyproject.toml" in ci_gate_text
        or "pyproject\\.toml" in pre_commit_text
        or "pyproject\\.toml" in ci_gate_text
    )
    if not has_pyproject_marker:
        failed_checks.append("root_whitelist_v2")

    return {
        "status": "pass" if not failed_checks else "fail",
        "failed_checks": failed_checks,
        "warnings": [] if not failed_checks else ["Hook/CI contract mismatch detected"],
    }


def check_gate_g5(workspace_root: Path) -> dict[str, Any]:
    hooks_dir = workspace_root / "tools" / "githooks"
    scripts_dir = workspace_root / "tools" / "scripts"

    pre_commit_path = hooks_dir / "pre-commit"
    pre_push_path = hooks_dir / "pre-push"
    commit_msg_path = hooks_dir / "commit-msg"
    ci_gate_path = scripts_dir / "run_quality_gates_ci.sh"

    missing = [
        str(p.relative_to(workspace_root))
        for p in [pre_commit_path, pre_push_path, commit_msg_path, ci_gate_path]
        if not p.exists()
    ]
    if missing:
        return {
            "status": "fail",
            "failed_checks": ["required_files"],
            "warnings": [f"Missing required files: {', '.join(missing)}"],
            "missing_files": missing,
        }

    result = validate_hook_contract(
        pre_commit_text=pre_commit_path.read_text(encoding="utf-8", errors="ignore"),
        pre_push_text=pre_push_path.read_text(encoding="utf-8", errors="ignore"),
        commit_msg_text=commit_msg_path.read_text(encoding="utf-8", errors="ignore"),
        ci_gate_text=ci_gate_path.read_text(encoding="utf-8", errors="ignore"),
    )
    result["missing_files"] = []
    return result
