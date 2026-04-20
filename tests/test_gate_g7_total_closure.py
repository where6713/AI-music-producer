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


def test_gate_g1_accepts_merge_head_when_next_subject_is_compliant(monkeypatch) -> None:
    from src.producer_tools.self_check import gate_g7

    monkeypatch.setattr(
        gate_g7,
        "_latest_commit_subjects",
        lambda _workspace_root, count=4: [
            "Merge 963b4035a0cffd9b36a065f81d7a1d9583d33ba5 into 905c79f1b4425366b455ca0bb0ba9d6672ef24d4",
            "feat(g7): add total-closure validator and gate-check all",
        ],
    )

    result = gate_g7._run_g1_check(Path.cwd())

    assert result["status"] == "pass"
    assert result.get("context") == "merge_commit_head"


def test_gate_g1_accepts_shallow_merge_head_without_history(monkeypatch) -> None:
    from src.producer_tools.self_check import gate_g7

    monkeypatch.setattr(
        gate_g7,
        "_latest_commit_subjects",
        lambda _workspace_root, count=4: [
            "Merge 9cd3d350e3872bfab893113fdf1f2fcc2484f708 into 905c79f1b4425366b455ca0bb0ba9d6672ef24d4",
        ],
    )

    result = gate_g7._run_g1_check(Path.cwd())

    assert result["status"] == "pass"
    assert result.get("context") == "merge_commit_head_shallow"
