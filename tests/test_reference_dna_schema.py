"""Tests for reference_dna.json schema validation."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

style_deconstructor = importlib.import_module(
    "producer_tools.business.style_deconstructor"
)


def test_reference_dna_output_has_required_fields(tmp_path: Path) -> None:
    """G2: reference_dna output must contain all required top-level fields."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    assert "tempo_key" in result
    assert "instrumentation" in result
    assert "energy_curve" in result


def test_tempo_key_schema_validation(tmp_path: Path) -> None:
    """G2: tempo_key must match schema with bpm, key, scale, structure."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    tempo_key = result["tempo_key"]
    assert isinstance(tempo_key["bpm"], (int, float))
    assert isinstance(tempo_key["key"], str)
    assert isinstance(tempo_key["scale"], str)
    assert isinstance(tempo_key["structure"], list)


def test_instrumentation_schema_validation(tmp_path: Path) -> None:
    """G2: instrumentation must be per-stem {stem: {presence, role}}."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    instr = result["instrumentation"]
    # Per-stem format: {stem_name: {presence: bool, role: str|None}}
    assert isinstance(instr, dict)
    for stem in ["vocals", "drums", "bass", "guitar", "piano", "other"]:
        if stem in instr:
            assert "presence" in instr[stem]
            assert "role" in instr[stem]


def test_energy_curve_schema_validation(tmp_path: Path) -> None:
    """G2: energy_curve entries must have time and energy fields."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    curve = result["energy_curve"]
    assert isinstance(curve, list)
    if len(curve) > 0:
        entry = curve[0]
        assert "time" in entry
        assert "energy" in entry
        assert isinstance(entry["time"], (int, float))
        assert isinstance(entry["energy"], (int, float))


def test_reference_dna_json_serializable(tmp_path: Path) -> None:
    """G2: output must be JSON serializable for reference_dna.json."""
    import json

    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    # Must not raise exception
    json_str = json.dumps(result)
    assert len(json_str) > 0

    # Must be reversible
    parsed = json.loads(json_str)
    assert parsed["ok"] is True
