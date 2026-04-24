from __future__ import annotations

from pathlib import Path
from typing import Any


def _extract_step_block(yaml_text: str, step_name: str) -> str:
    marker = f"- name: {step_name}"
    start = yaml_text.find(marker)
    if start < 0:
        return ""
    next_idx = yaml_text.find("\n      - name:", start + len(marker))
    if next_idx < 0:
        return yaml_text[start:]
    return yaml_text[start:next_idx]


def validate_g6_contract(*, workflow_yaml: str, ci_script: str) -> dict[str, Any]:
    failed_checks: list[str] = []

    if "ci-quality-gates:" not in workflow_yaml:
        failed_checks.append("workflow_job_name")

    install_block = _extract_step_block(workflow_yaml, "Install Python test deps")
    if not install_block:
        failed_checks.append("workflow_install_step")
    else:
        if "pip install ." not in install_block:
            failed_checks.append("workflow_project_install")
        if "pip install pytest" not in install_block:
            failed_checks.append("workflow_pytest_install")

    run_block = _extract_step_block(workflow_yaml, "Run mirrored quality gates")
    if not run_block:
        failed_checks.append("workflow_run_step")
    elif "tools/scripts/run_quality_gates_ci.sh" not in run_block:
        failed_checks.append("workflow_ci_script_invocation")

    if "pytest -q" not in ci_script:
        failed_checks.append("ci_pytest_execution")

    if "out/lyrics.txt" not in ci_script:
        failed_checks.append("ci_output_contract_assertion")

    return {
        "status": "pass" if not failed_checks else "fail",
        "failed_checks": failed_checks,
        "warnings": [],
    }


def check_gate_g6(workspace_root: Path) -> dict[str, Any]:
    workflow_path = workspace_root / ".github" / "workflows" / "quality-gates.yml"
    ci_script_path = workspace_root / "tools" / "scripts" / "run_quality_gates_ci.sh"

    missing = [
        str(p.relative_to(workspace_root))
        for p in [workflow_path, ci_script_path]
        if not p.exists()
    ]
    if missing:
        return {
            "status": "fail",
            "failed_checks": ["required_files"],
            "warnings": [f"Missing required files: {', '.join(missing)}"],
            "missing_files": missing,
        }

    result = validate_g6_contract(
        workflow_yaml=workflow_path.read_text(encoding="utf-8", errors="ignore"),
        ci_script=ci_script_path.read_text(encoding="utf-8", errors="ignore"),
    )
    result["missing_files"] = []
    return result
