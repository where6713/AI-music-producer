from __future__ import annotations

from pathlib import Path


def test_gate_g0_environment_contract_passes() -> None:
    from src.producer_tools.self_check.gate_g0 import check_gate_g0

    result = check_gate_g0(Path.cwd(), strict_hooks_path=False)

    assert result["status"] == "pass"
    assert result["required_hooks"] == [
        "pre-commit",
        "commit-msg",
        "pre-push",
        "post-commit",
    ]
    assert result["missing_hooks"] == []
    assert isinstance(result["warnings"], list)


def test_gate_g0_strict_hooks_path_fails_when_mismatch(tmp_path: Path, monkeypatch) -> None:
    from src.producer_tools.self_check import gate_g0

    hooks_dir = tmp_path / "tools" / "githooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for hook_name in ["pre-commit", "commit-msg", "pre-push", "post-commit"]:
        (hooks_dir / hook_name).write_text("#!/usr/bin/env sh\n", encoding="utf-8")

    monkeypatch.setattr(gate_g0, "_read_hooks_path", lambda _: ".git/hooks")

    result = gate_g0.check_gate_g0(tmp_path, strict_hooks_path=True)

    assert result["status"] == "fail"
    assert result["hooks_path_ok"] is False
    assert result["missing_hooks"] == []
    assert result["warnings"]
