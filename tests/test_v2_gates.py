from __future__ import annotations

import re
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
            "manifest_path": "docs/ai_doc_manifest.json",
            "delivery_files": ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"],
            "field_name_conflicts": [],
        }
    )
    assert result["status"] == "pass"


def test_g5_hook_contract_pass() -> None:
    pre_commit = "git diff --cached --name-only --diff-filter=ACMRD"
    pre_push = "oost-hook-ledger\npytest -q\npython -m apps.cli.main pm-audit\nout/lyrics.txt\nout/style.txt\nout/exclude.txt\ngit commit --amend --no-edit"
    commit_msg = "type(scope): summary"
    ci = "placeholder/mock markers detected\npytest -q\npython -m apps.cli.main pm-audit --run-id ci-gate-audit\nout/lyrics.txt\nout/style.txt\nout/exclude.txt\npyproject.toml"

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
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
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


def test_g6_ci_contract_pass_with_checkout_fetch_depth_zero() -> None:
    workflow = """
jobs:
  ci-quality-gates:
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
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


def test_g5_hook_contract_fail_without_ledger_policy() -> None:
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


def test_g5_hook_contract_fail_without_pm_audit_parity() -> None:
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
    assert result["status"] == "fail"
    assert "hook_ci_pm_audit_parity" in result["failed_checks"]


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


def test_g3_pass_evidence_contract_requires_outputs() -> None:
    from src.producer_tools.self_check.gate_g3 import validate_pass_evidence

    result = validate_pass_evidence(
        {
            "local_command": "pytest -q",
            "local_result": "pass",
            "ci_result": "success",
            "ci_run_url": "https://github.com/where6713/AI-music-producer/actions/runs/1",
            "reproducible_commands": ["pytest -q", "python -m apps.cli.main gate-check --all"],
            "local_output": "25 passed",
            "ci_output": "ci-quality-gates: success",
        }
    )
    assert result["status"] == "pass"


def test_ci_legacy_residue_scan_excludes_ci_script_self_match() -> None:
    script = Path("tools/scripts/run_quality_gates_ci.sh").read_text(encoding="utf-8")
    legacy_block = re.search(
        r"# 4\.2\) PM hard-stop: legacy v1\.1 middleware residue forbidden\n(.*?)(?:\n\n# 5\)|\Z)",
        script,
        flags=re.DOTALL,
    )
    assert legacy_block is not None
    assert "':!tools/scripts/run_quality_gates_ci.sh'" in legacy_block.group(1)


def test_pytest_asyncio_default_loop_scope_is_configured() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "asyncio_default_fixture_loop_scope" in pyproject
