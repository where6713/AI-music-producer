from __future__ import annotations

from pathlib import Path
from typing import Any
import re


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_step_block(yaml_text: str, step_name: str) -> str:
    marker = f"- name: {step_name}"
    start = yaml_text.find(marker)
    if start < 0:
        return ""
    next_idx = yaml_text.find("\n      - name:", start + len(marker))
    if next_idx < 0:
        return yaml_text[start:]
    return yaml_text[start:next_idx]


def _contains_requirement_baseline(req_text: str) -> bool:
    reqs = [line.strip() for line in req_text.splitlines() if line.strip()]
    checks = {
        "openai==": False,
        "typer==": False,
        "librosa==": False,
        "pypinyin==": False,
    }
    for line in reqs:
        for key in list(checks.keys()):
            if line.startswith(key):
                checks[key] = True
    return all(checks.values())


def validate_g6_contract(
    *,
    workflow_yaml: str,
    ci_script: str,
    requirements_text: str,
) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    if "ci-quality-gates:" not in workflow_yaml:
        failed_checks.append("workflow_job_name")

    install_block = _extract_step_block(workflow_yaml, "Install Python test deps")
    if not install_block:
        failed_checks.append("workflow_install_step")
    else:
        if "pip install -r apps/cli/requirements.txt" not in install_block:
            failed_checks.append("workflow_requirements_install")
        if "pip install pytest" not in install_block:
            failed_checks.append("workflow_pytest_install")

    run_block = _extract_step_block(workflow_yaml, "Run mirrored quality gates")
    if not run_block:
        failed_checks.append("workflow_run_step")
    elif "tools/scripts/run_quality_gates_ci.sh" not in run_block:
        failed_checks.append("workflow_ci_script_invocation")

    if "placeholder/mock markers detected" not in ci_script:
        failed_checks.append("ci_placeholder_scan")

    if "SHOW-ME-OUTPUT" not in ci_script:
        failed_checks.append("ci_show_me_output")

    if "pytest -q" not in ci_script:
        failed_checks.append("ci_pytest_execution")

    if "run_id" not in ci_script or "trace_id" not in ci_script:
        warnings.append("ci script does not explicitly assert ledger run_id/trace_id fields")

    if not _contains_requirement_baseline(requirements_text):
        failed_checks.append("requirements_baseline")

    status = "pass" if not failed_checks else "fail"
    return {
        "status": status,
        "failed_checks": failed_checks,
        "warnings": warnings,
    }


def check_gate_g6(workspace_root: Path) -> dict[str, Any]:
    workflow_path = workspace_root / ".github" / "workflows" / "quality-gates.yml"
    ci_script_path = workspace_root / "tools" / "scripts" / "run_quality_gates_ci.sh"
    requirements_path = workspace_root / "apps" / "cli" / "requirements.txt"

    missing_files = [
        str(path.relative_to(workspace_root))
        for path in [workflow_path, ci_script_path, requirements_path]
        if not path.exists()
    ]
    if missing_files:
        return {
            "status": "fail",
            "failed_checks": ["required_files"],
            "warnings": [f"Missing required files: {', '.join(missing_files)}"],
            "missing_files": missing_files,
        }

    result = validate_g6_contract(
        workflow_yaml=_read_text(workflow_path),
        ci_script=_read_text(ci_script_path),
        requirements_text=_read_text(requirements_path),
    )
    result["missing_files"] = []
    return result
