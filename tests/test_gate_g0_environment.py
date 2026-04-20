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
