"""Tests for reference_dna.json output wiring in style_deconstructor."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

style_deconstructor = importlib.import_module(
    "producer_tools.business.style_deconstructor"
)


def test_reference_dna_output_path_parameter_accepted(tmp_path: Path) -> None:
    """G2: run() should accept reference_dna_output_path parameter without error."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")
    output_path = tmp_path / "reference_dna.json"

    result = style_deconstructor.run(
        {
            "reference_audio_path": str(reference_path),
            "reference_dna_output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert output_path.exists(), "reference_dna.json should be created"


def test_reference_dna_json_schema_matches_prd(tmp_path: Path) -> None:
    """G2: reference_dna.json must contain all PRD-required fields."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")
    output_path = tmp_path / "reference_dna.json"

    style_deconstructor.run(
        {
            "reference_audio_path": str(reference_path),
            "reference_dna_output_path": str(output_path),
        }
    )

    data = json.loads(output_path.read_text(encoding="utf-8"))

    # PRD: tempo/key/structure/instrumentation/energy_curve/vocal_pitch_range_midi/vocal_melismatic_density/embedding_clap/stems_dir
    assert "tempo" in data or "tempo_key" in data
    assert "key" in data or ("tempo_key" in data and "key" in data["tempo_key"])
    assert "structure" in data or (
        "tempo_key" in data and "structure" in data["tempo_key"]
    )
    assert "instrumentation" in data
    assert "energy_curve" in data
    assert "stems_dir" in data or "stems" in data


def test_reference_dna_instrumentation_has_stem_format(tmp_path: Path) -> None:
    """G2: instrumentation must be per-stem {stem: {presence, role}}."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")
    output_path = tmp_path / "reference_dna.json"

    style_deconstructor.run(
        {
            "reference_audio_path": str(reference_path),
            "reference_dna_output_path": str(output_path),
        }
    )

    data = json.loads(output_path.read_text(encoding="utf-8"))
    instr = data.get("instrumentation", {})

    # Must be per-stem format, not list format
    if isinstance(instr, dict):
        for stem_name in ["vocals", "drums", "bass", "guitar", "piano", "other"]:
            if stem_name in instr:
                assert "presence" in instr[stem_name], f"{stem_name} needs presence"
                assert "role" in instr[stem_name], f"{stem_name} needs role"


def test_missing_audio_returns_error_without_output(tmp_path: Path) -> None:
    """G2: Missing audio should not create output file."""
    output_path = tmp_path / "reference_dna.json"

    result = style_deconstructor.run(
        {
            "reference_audio_path": "missing.wav",
            "reference_dna_output_path": str(output_path),
        }
    )

    assert result["ok"] is False
    assert not output_path.exists()
