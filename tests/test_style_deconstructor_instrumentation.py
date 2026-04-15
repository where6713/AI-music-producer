"""Tests for instrumentation and energy curve extraction in style_deconstructor."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

style_deconstructor = importlib.import_module(
    "producer_tools.business.style_deconstructor"
)


def test_instrumentation_returns_dict(tmp_path: Path) -> None:
    """G2: instrumentation dict should be present in result."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    assert "instrumentation" in result
    assert isinstance(result["instrumentation"], dict)


def test_instrumentation_has_stem_format(tmp_path: Path) -> None:
    """G2: instrumentation should be per-stem {presence, role}."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    instr = result["instrumentation"]
    assert isinstance(instr, dict)
    # Per-stem format
    for stem in ["vocals", "drums", "bass", "guitar", "piano", "other"]:
        if stem in instr:
            assert "presence" in instr[stem]
            assert "role" in instr[stem]


def test_energy_curve_returns_list(tmp_path: Path) -> None:
    """G2: energy_curve should be present as list."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    assert "energy_curve" in result
    assert isinstance(result["energy_curve"], list)


def test_energy_curve_has_time_energy_pairs(tmp_path: Path) -> None:
    """G2: energy_curve entries should have time and energy fields."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    if len(result["energy_curve"]) > 0:
        first_entry = result["energy_curve"][0]
        assert "time" in first_entry
        assert "energy" in first_entry


def test_missing_audio_returns_error_without_instrumentation() -> None:
    """G2: Missing reference should not include instrumentation in error response."""
    result = style_deconstructor.run({"reference_audio_path": "missing.wav"})

    assert result["ok"] is False
    assert "instrumentation" not in result or result.get("instrumentation") is None
