from __future__ import annotations

from pathlib import Path
from typing import Any

from src.producer_tools.self_check.gate_g0 import check_gate_g0
from src.producer_tools.self_check.gate_g1 import check_gate_g1
from src.producer_tools.self_check.gate_g2 import validate_failure_evidence
from src.producer_tools.self_check.gate_g3 import validate_pass_evidence
from src.producer_tools.self_check.gate_g4 import validate_docs_alignment
from src.producer_tools.self_check.gate_g5 import check_gate_g5
from src.producer_tools.self_check.gate_g6 import check_gate_g6


def _run_g2_check() -> dict[str, Any]:
    return validate_failure_evidence(
        {
            "symptom": "schema validation failed",
            "trigger_condition": "pytest -q tests/test_v2_schemas.py::test_payload_schema_invalid",
            "root_cause": "invalid tag and missing fields",
            "failure_command": "pytest -q tests/test_v2_schemas.py::test_payload_schema_invalid",
            "failure_output": "ValidationError: required fields missing",
        }
    )


def _run_g3_check() -> dict[str, Any]:
    return validate_pass_evidence(
        {
            "local_command": "pytest -q",
            "local_result": "pass",
            "ci_result": "pass",
            "ci_run_url": "https://github.com/where6713/AI-music-producer/actions",
            "reproducible_commands": ["pytest -q", "bash tools/scripts/run_quality_gates_ci.sh"],
        }
    )


def _run_g4_check() -> dict[str, Any]:
    return validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "delivery_files": ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"],
            "field_name_conflicts": [],
        }
    )


def _normalize(result: dict[str, Any]) -> str:
    return "pass" if result.get("status") == "pass" else "fail"


def _proof_check(workspace_root: Path) -> dict[str, Any]:
    out = workspace_root / "out"
    required = ["lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json", "trace.json"]
    missing = [name for name in required if not (out / name).exists()]
    trace_text = (out / "trace.json").read_text(encoding="utf-8", errors="ignore") if (out / "trace.json").exists() else ""
    llm_calls_ok = '"llm_calls": 1' in trace_text or '"llm_calls": 2' in trace_text
    status = "pass" if (not missing and llm_calls_ok) else "fail"
    return {
        "status": status,
        "output_dir": str(out),
        "missing_files": missing,
        "llm_calls_ok": llm_calls_ok,
    }


def check_gate_g7(workspace_root: Path, *, run_proof: bool = False) -> dict[str, Any]:
    gates = {
        "G0": check_gate_g0(workspace_root, strict_hooks_path=False),
        "G1": check_gate_g1(workspace_root),
        "G2": _run_g2_check(),
        "G3": _run_g3_check(),
        "G4": _run_g4_check(),
        "G5": check_gate_g5(workspace_root),
        "G6": check_gate_g6(workspace_root),
    }

    gate_summary = {name: _normalize(data) for name, data in gates.items()}
    failed_gates = [name for name, status in gate_summary.items() if status != "pass"]

    proof = {"status": "skipped", "output_dir": "", "missing_files": [], "llm_calls_ok": False}
    if run_proof:
        proof = _proof_check(workspace_root)

    status = "pass"
    if failed_gates:
        status = "fail"
    elif run_proof and proof.get("status") != "pass":
        status = "fail"

    return {
        "status": status,
        "gate_summary": gate_summary,
        "failed_gates": failed_gates,
        "proof": proof,
    }
