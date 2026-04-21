from __future__ import annotations

from pathlib import Path

from src.producer_tools.self_check.gate_g4 import validate_docs_alignment
from src.producer_tools.self_check.gate_g5 import validate_hook_contract
from src.producer_tools.self_check.gate_g6 import validate_g6_contract


def test_g4_docs_alignment_pass() -> None:
    result = validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "delivery_files": ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"],
            "field_name_conflicts": [],
        }
    )
    assert result["status"] == "pass"


def test_g5_hook_contract_pass() -> None:
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
    assert result["status"] == "pass"


def test_g6_ci_contract_pass() -> None:
    workflow = """
jobs:
  ci-quality-gates:
    steps:
      - name: Install Python test deps
        run: |
          pip install .
          pip install pytest
      - name: Run mirrored quality gates
        run: |
          tools/scripts/run_quality_gates_ci.sh
"""
    ci_script = "pytest -q\nout/lyrics.txt"
    result = validate_g6_contract(workflow_yaml=workflow, ci_script=ci_script)
    assert result["status"] == "pass"


def test_g2_failure_evidence_contract_requires_failure_output() -> None:
    from src.producer_tools.self_check.gate_g2 import validate_failure_evidence

    result = validate_failure_evidence(
        {
            "symptom": "symptom",
            "trigger_condition": "trigger",
            "root_cause": "root",
            "failure_command": "cmd",
            "failure_output": "stderr snapshot",
        }
    )
    assert result["status"] == "pass"
