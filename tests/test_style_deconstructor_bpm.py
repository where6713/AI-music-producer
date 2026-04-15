"""Tests for BPM/key/structure extraction in style_deconstructor."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

style_deconstructor = importlib.import_module(
    "producer_tools.business.style_deconstructor"
)


def test_bpm_extraction_returns_tempo_key_dict(tmp_path: Path) -> None:
    """G2: tempo_key dict should be present in result with bpm field."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    assert "tempo_key" in result
    assert "bpm" in result["tempo_key"]
    assert isinstance(result["tempo_key"]["bpm"], (int, float))


def test_key_extraction_returns_key_and_scale(tmp_path: Path) -> None:
    """G2: tempo_key dict should contain key and scale fields."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    assert "tempo_key" in result
    assert "key" in result["tempo_key"]
    assert "scale" in result["tempo_key"]
    assert isinstance(result["tempo_key"]["key"], str)
    assert isinstance(result["tempo_key"]["scale"], str)


def test_structure_extraction_returns_sections(tmp_path: Path) -> None:
    """G2: tempo_key dict should contain structure with sections list."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    assert "tempo_key" in result
    assert "structure" in result["tempo_key"]
    assert isinstance(result["tempo_key"]["structure"], list)


def test_missing_audio_returns_error_without_tempo_key() -> None:
    """G2: Missing reference should not include tempo_key in error response."""
    result = style_deconstructor.run({"reference_audio_path": "missing.wav"})

    assert result["ok"] is False
    assert "tempo_key" not in result or result.get("tempo_key") is None
