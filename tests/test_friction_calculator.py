"""Tests for friction_calculator hard-constraint scoring."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


def test_friction_calculator_returns_hard_constraints_score(tmp_path: Path) -> None:
    """G2: friction_calculator should return hard_constraints dict with score."""
    from src.producer_tools.business.friction_calculator import (
        calculate_hard_constraints,
    )

    voice_profile = {
        "f0": {"median": 220.0, "p10": 180.0, "p90": 280.0},
        "formants": {"f1": 500.0, "f2": 1500.0, "f3": 2500.0},
        "timbre": {"hnr": 10.0, "jitter": 0.02, "shimmer": 0.03},
        "dynamics": {"intensity_range": 20.0},
    }
    reference_dna = {
        "tempo": 120.0,
        "key": "C",
        "scale": "major",
        "instrumentation": {"vocals": {"presence": True, "role": "lead_vocal"}},
    }

    result = calculate_hard_constraints(voice_profile)

    assert result["ok"] is True
    assert "hard_constraints" in result
    assert "score" in result["hard_constraints"]


def test_friction_calculator_scores_voice_range_compatibility(tmp_path: Path) -> None:
    """G2: voice range compatibility should return 0-100 score."""
    from src.producer_tools.business.friction_calculator import (
        calculate_hard_constraints,
    )

    voice_profile = {
        "f0": {"median": 220.0, "p10": 180.0, "p90": 280.0},
        "formants": {"f1": 500.0, "f2": 1500.0, "f3": 2500.0},
        "timbre": {"hnr": 10.0, "jitter": 0.02, "shimmer": 0.03},
        "dynamics": {"intensity_range": 20.0},
    }
    reference_dna = {
        "tempo": 120.0,
        "key": "C",
        "scale": "major",
        "instrumentation": {"vocals": {"presence": True, "role": "lead_vocal"}},
    }

    result = calculate_hard_constraints(voice_profile)

    assert 0 <= result["hard_constraints"]["score"] <= 100


def test_friction_calculator_missing_voice_profile_returns_error(
    tmp_path: Path,
) -> None:
    """G2: Missing voice_profile should return error."""
    from src.producer_tools.business.friction_calculator import (
        calculate_hard_constraints,
    )

    result = calculate_hard_constraints(None)

    assert result["ok"] is False


def test_timbre_fit_scoring(tmp_path: Path) -> None:
    """G2: timbre fit should return cosine similarity score 0-100."""
    from src.producer_tools.business.friction_calculator import calculate_timbre_fit

    # Identical embeddings should return 100
    identical_embedding = [0.5] * 512
    voice_profile = {"embedding_clap": identical_embedding}
    reference_dna = {"embedding_clap": identical_embedding}

    result = calculate_timbre_fit(voice_profile, reference_dna)

    assert result["ok"] is True
    assert "timbre_fit" in result
    assert "score" in result["timbre_fit"]
    assert result["timbre_fit"]["score"] == 100.0


def test_timbre_fit_opposite_embeddings(tmp_path: Path) -> None:
    """G2: opposite embeddings should return low score."""
    from src.producer_tools.business.friction_calculator import calculate_timbre_fit

    # Opposite embeddings should have low similarity
    voice_profile = {"embedding_clap": [1.0] * 512}
    reference_dna = {"embedding_clap": [-1.0] * 512}

    result = calculate_timbre_fit(voice_profile, reference_dna)

    assert result["ok"] is True
    assert result["timbre_fit"]["score"] < 10.0


def test_timbre_fit_missing_embeddings(tmp_path: Path) -> None:
    """G2: missing embeddings should return error gracefully."""
    from src.producer_tools.business.friction_calculator import calculate_timbre_fit

    # Missing embedding_clap in voice_profile
    result = calculate_timbre_fit({}, {"embedding_clap": [0.5] * 512})

    assert result["ok"] is False

    # Missing embedding_clap in reference_dna
    result = calculate_timbre_fit({"embedding_clap": [0.5] * 512}, {})

    assert result["ok"] is False


def test_timbre_fit_score_in_range(tmp_path: Path) -> None:
    """G2: timbre fit score should always be 0-100."""
    from src.producer_tools.business.friction_calculator import calculate_timbre_fit

    import random

    # Random embeddings
    voice_emb = [random.uniform(-1, 1) for _ in range(512)]
    ref_emb = [random.uniform(-1, 1) for _ in range(512)]

    result = calculate_timbre_fit(
        {"embedding_clap": voice_emb}, {"embedding_clap": ref_emb}
    )

    assert result["ok"] is True
    assert 0 <= result["timbre_fit"]["score"] <= 100


def test_generate_verdict_accept(tmp_path: Path) -> None:
    """G2: high scores should return 'accept' verdict."""
    from src.producer_tools.business.friction_calculator import generate_verdict

    # High scores = good fit
    result = generate_verdict(hard_constraints_score=90.0, timbre_fit_score=85.0)

    assert result["verdict"] == "accept"
    assert result["overall_friction_index"] < 20.0


def test_generate_verdict_adjust(tmp_path: Path) -> None:
    """G2: medium scores should return 'adjust' verdict."""
    from src.producer_tools.business.friction_calculator import generate_verdict

    # Medium scores = needs adjustment
    result = generate_verdict(hard_constraints_score=60.0, timbre_fit_score=50.0)

    assert result["verdict"] == "adjust"
    assert 20.0 <= result["overall_friction_index"] <= 60.0


def test_generate_verdict_reject(tmp_path: Path) -> None:
    """G2: low scores should return 'reject' verdict."""
    from src.producer_tools.business.friction_calculator import generate_verdict

    # Low scores = poor fit
    result = generate_verdict(hard_constraints_score=30.0, timbre_fit_score=20.0)

    assert result["verdict"] == "reject"
    assert result["overall_friction_index"] > 60.0


def test_generate_adjustments(tmp_path: Path) -> None:
    """G2: should generate recommended adjustments."""
    from src.producer_tools.business.friction_calculator import generate_adjustments

    voice_profile = {
        "f0": {"median": 300.0, "p10": 250.0, "p90": 350.0},  # High voice
    }
    reference_dna = {
        "tempo": 140.0,
        "key": "G",
        "scale": "major",
    }

    result = generate_adjustments(voice_profile, reference_dna)

    assert "transpose_semitones" in result
    assert "target_key" in result
    assert "tempo_bpm" in result
    assert "vocal_style_tags" in result


def test_friction_report_full(tmp_path: Path) -> None:
    """G2: should generate full friction_report."""
    from src.producer_tools.business.friction_calculator import generate_friction_report

    voice_profile = {
        "f0": {"median": 220.0, "p10": 180.0, "p90": 280.0},
        "embedding_clap": [0.5] * 512,
    }
    reference_dna = {
        "tempo": 120.0,
        "key": "C",
        "scale": "major",
        "embedding_clap": [0.5] * 512,
    }

    result = generate_friction_report(voice_profile, reference_dna)

    assert result["ok"] is True
    assert "overall_friction_index" in result
    assert "verdict" in result
    assert "conflicts" in result
    assert "recommended_adjustments" in result


def test_friction_report_output_to_file(tmp_path: Path) -> None:
    """G2: should output friction_report.json to file."""
    import json

    from src.producer_tools.business.friction_calculator import run

    voice_profile = {
        "f0": {"median": 220.0, "p10": 180.0, "p90": 280.0},
        "embedding_clap": [0.5] * 512,
    }
    reference_dna = {
        "tempo": 120.0,
        "key": "C",
        "scale": "major",
        "embedding_clap": [0.5] * 512,
    }
    output_path = tmp_path / "friction_report.json"

    result = run(
        {
            "voice_profile": voice_profile,
            "reference_dna": reference_dna,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert output_path.exists()

    # Verify JSON is valid and has required fields
    with open(output_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "overall_friction_index" in report
    assert "verdict" in report
    assert "conflicts" in report
    assert "recommended_adjustments" in report


def test_friction_report_schema_validation(tmp_path: Path) -> None:
    """G2: friction_report should match PRD schema."""
    import json

    from src.producer_tools.business.friction_calculator import generate_friction_report

    voice_profile = {
        "f0": {"median": 220.0, "p10": 180.0, "p90": 280.0},
        "embedding_clap": [0.5] * 512,
    }
    reference_dna = {
        "tempo": 120.0,
        "key": "C",
        "scale": "major",
        "embedding_clap": [0.5] * 512,
    }

    result = generate_friction_report(voice_profile, reference_dna)

    # Schema validation: required fields
    required_fields = [
        "overall_friction_index",
        "verdict",
        "conflicts",
        "recommended_adjustments",
    ]

    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    # recommended_adjustments sub-fields
    adj = result["recommended_adjustments"]
    adj_fields = [
        "transpose_semitones",
        "target_key",
        "tempo_bpm",
        "vocal_style_tags",
        "instrumentation_emphasis",
        "instrumentation_deemphasis",
        "structure_modifications",
    ]

    for field in adj_fields:
        assert field in adj, f"Missing adjustment field: {field}"

    # Type validation
    assert isinstance(result["overall_friction_index"], (int, float))
    assert isinstance(result["verdict"], str)
    assert isinstance(result["conflicts"], list)
    assert result["verdict"] in ("accept", "adjust", "reject")
