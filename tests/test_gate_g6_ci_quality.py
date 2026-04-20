from __future__ import annotations

from pathlib import Path


def test_gate_g6_fails_without_show_me_output_check() -> None:
    from src.producer_tools.self_check.gate_g6 import validate_g6_contract

    workflow_yaml = """
name: quality-gates
jobs:
  ci-quality-gates:
    steps:
      - name: Install Python test deps
        run: |
          pip install -r apps/cli/requirements.txt
          pip install pytest
      - name: Run mirrored quality gates
        run: tools/scripts/run_quality_gates_ci.sh
""".strip()

    ci_script = """
echo '[ci-gates] start'
echo '[ci-gates] pytest -q'
""".strip()

    requirements_text = """
openai==1.30
typer==0.12
librosa==0.10.2
pypinyin==0.51
""".strip()

    result = validate_g6_contract(
        workflow_yaml=workflow_yaml,
        ci_script=ci_script,
        requirements_text=requirements_text,
    )

    assert result["status"] == "fail"
    assert "ci_show_me_output" in result["failed_checks"]


def test_gate_g6_passes_current_repo_contract() -> None:
    from src.producer_tools.self_check.gate_g6 import check_gate_g6

    result = check_gate_g6(Path.cwd())

    assert result["status"] == "pass"
    assert result["failed_checks"] == []
