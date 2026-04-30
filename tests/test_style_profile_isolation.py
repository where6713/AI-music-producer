from __future__ import annotations

from src.compile import write_outputs
from tests.test_v2_compile import _payload


def test_style_uses_current_active_profile_and_bpm(tmp_path) -> None:
    payload = _payload()
    trace = {
        "llm_calls": 1,
        "active_profile": "club_dance",
        "profile_source": "cli_override",
        "prosody_contract": {
            "bpm": 128,
            "syllable_budget_min": 180,
            "syllable_budget_max": 260,
            "verse_line_max": 7,
            "chorus_line_max": 6,
            "bridge_line_max": 8,
        },
    }

    write_outputs(payload, tmp_path, trace)
    style = (tmp_path / "style.txt").read_text(encoding="utf-8")

    assert "profile:club_dance" in style
    assert "128 BPM" in style
    assert "profile:urban_introspective" not in style


def test_style_changes_per_run_without_inheriting_previous_profile(tmp_path) -> None:
    payload = _payload()

    trace_first = {
        "llm_calls": 1,
        "active_profile": "urban_introspective",
        "profile_source": "cli_override",
        "prosody_contract": {
            "bpm": 85,
            "syllable_budget_min": 180,
            "syllable_budget_max": 240,
            "verse_line_max": 10,
            "chorus_line_max": 8,
            "bridge_line_max": 12,
        },
    }
    trace_second = {
        "llm_calls": 1,
        "active_profile": "classical_restraint",
        "profile_source": "corpus_vote",
        "prosody_contract": {
            "bpm": 72,
            "syllable_budget_min": 160,
            "syllable_budget_max": 220,
            "verse_line_max": 9,
            "chorus_line_max": 7,
            "bridge_line_max": 13,
        },
    }

    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    write_outputs(payload, run_a, trace_first)
    write_outputs(payload, run_b, trace_second)

    style_a = (run_a / "style.txt").read_text(encoding="utf-8")
    style_b = (run_b / "style.txt").read_text(encoding="utf-8")

    assert "profile:urban_introspective" in style_a
    assert "85 BPM" in style_a
    assert "profile:classical_restraint" not in style_a

    assert "profile:classical_restraint" in style_b
    assert "72 BPM" in style_b
    assert "profile:urban_introspective" not in style_b
