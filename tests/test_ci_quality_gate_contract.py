"""Contract tests for CI quality gate hard-stop policies."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ci_quality_gates_blocks_placeholder_and_mock_markers() -> None:
    """G7 must reject placeholder/mock markers in tracked files."""
    script = PROJECT_ROOT / "tools" / "scripts" / "run_quality_gates_ci.sh"
    text = script.read_text(encoding="utf-8")

    assert "mock_data" in text
    assert "Lorem ipsum" in text
    assert "TODO_FILL" in text


def test_ci_quality_gates_has_show_me_output_step() -> None:
    """G8 must print a real assembled prompt in CI logs."""
    script = PROJECT_ROOT / "tools" / "scripts" / "run_quality_gates_ci.sh"
    text = script.read_text(encoding="utf-8")

    assert "assemble_system_prompt_from_assets" in text
    assert "SHOW-ME-OUTPUT" in text
    assert "system_prompt" in text
