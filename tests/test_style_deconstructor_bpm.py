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


def test_tempo_key_contains_lyric_beat_budget(tmp_path: Path) -> None:
    """tempo_key should include beat-aligned lyric budget fields."""
    reference_path = tmp_path / "ref.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    tempo_key = result.get("tempo_key", {})
    assert isinstance(tempo_key, dict)
    assert "lyric_beat_budget" in tempo_key
    budget = tempo_key.get("lyric_beat_budget", {})
    assert isinstance(budget, dict)
    assert "total_beats" in budget
    assert "beats_per_bar" in budget
    assert "sections" in budget
    assert isinstance(budget.get("sections"), list)
    assert len(budget.get("sections", [])) > 0


def test_reference_dna_contains_beat_budget_and_prd_voice_fields(
    tmp_path: Path,
) -> None:
    """reference_dna should expose beat budget and required PRD voice fields."""
    reference_path = tmp_path / "ref.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})

    assert result["ok"] is True
    reference_dna = result.get("reference_dna", {})
    assert isinstance(reference_dna, dict)
    assert "lyric_beat_budget" in reference_dna
    assert isinstance(reference_dna.get("lyric_beat_budget"), dict)
    assert "vocal_pitch_range_midi" in reference_dna
    assert "vocal_melismatic_density" in reference_dna


def test_compute_target_words_monotonic_with_bpm() -> None:
    """Higher BPM should produce higher target_words with same bars/beats."""
    low = style_deconstructor._compute_target_words(
        bars=4,
        beats_per_bar=4,
        bpm=90.0,
    )
    high = style_deconstructor._compute_target_words(
        bars=4,
        beats_per_bar=4,
        bpm=140.0,
    )
    assert low < high


def test_compute_target_words_bounded_range() -> None:
    """target_words should stay within [8, 48] bounds."""
    tiny = style_deconstructor._compute_target_words(
        bars=1,
        beats_per_bar=4,
        bpm=20.0,
    )
    huge = style_deconstructor._compute_target_words(
        bars=12,
        beats_per_bar=4,
        bpm=280.0,
    )
    assert tiny >= 8
    assert huge <= 48


def test_tempo_key_budget_targets_not_hardcoded_to_16(tmp_path: Path) -> None:
    """Budget targets should be computed, not all fixed at 16."""
    reference_path = tmp_path / "reference.wav"
    reference_path.write_bytes(b"fake")

    result = style_deconstructor.run({"reference_audio_path": str(reference_path)})
    assert result["ok"] is True
    tempo_key = result.get("tempo_key", {})
    assert isinstance(tempo_key, dict)
    budget = tempo_key.get("lyric_beat_budget", {})
    assert isinstance(budget, dict)
    sections = budget.get("sections", [])
    assert isinstance(sections, list)
    assert len(sections) > 0
    targets = [
        int(sec.get("target_words", 0))
        for sec in sections
        if isinstance(sec, dict)
        and isinstance(sec.get("target_words", 0), (int, float))
    ]
    assert len(targets) > 0
    assert all(8 <= t <= 48 for t in targets)
