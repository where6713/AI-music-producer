from __future__ import annotations

from pathlib import Path


def test_gate_g7_reports_fail_when_any_previous_gate_fails(monkeypatch) -> None:
    from src.producer_tools.self_check import gate_g7

    monkeypatch.setattr(
        gate_g7,
        "check_gate_g6",
        lambda _workspace_root: {"status": "fail", "failed_checks": ["x"]},
    )

    result = gate_g7.check_gate_g7(Path.cwd(), run_proof=False)

    assert result["status"] == "fail"
    assert "G6" in result["failed_gates"]


def test_gate_g7_reports_pass_when_all_previous_gates_pass() -> None:
    from src.producer_tools.self_check.gate_g7 import check_gate_g7

    result = check_gate_g7(Path.cwd(), run_proof=False)

    assert result["status"] == "pass"
    assert result["failed_gates"] == []
    assert result["proof"]["status"] == "skipped"
    assert result["gate_summary"]["G1"] == "pass"
