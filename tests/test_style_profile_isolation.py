from __future__ import annotations

import json
from pathlib import Path

from src.compile import write_outputs
from tests.test_v2_compile import _payload


def _seed_style_knowledge(base: Path) -> None:
    knowledge_dir = base / "corpus" / "_knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "by_profile": {
            "urban_introspective": {
                "genre": ["indie pop", "bedroom pop"],
                "mood": ["melancholic"],
                "vocal": ["intimate vocals"],
                "instruments": ["soft piano", "warm bass"],
                "production": ["lo-fi", "close mic"],
            },
            "classical_restraint": {
                "genre": ["Chinese traditional", "ancient Chinese"],
                "mood": ["ethereal"],
                "vocal": ["traditional Chinese female vocals"],
                "instruments": ["guqin", "pipa"],
                "production": ["natural reverb", "spacious"],
            },
            "club_dance": {
                "genre": ["EDM", "house"],
                "mood": ["euphoric"],
                "vocal": ["processed vocals"],
                "instruments": ["lead synth", "sub bass"],
                "production": ["loud master", "drop-ready"],
            },
        }
    }
    (knowledge_dir / "suno_style_vocab.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_style_uses_current_active_profile_and_bpm(tmp_path) -> None:
    _seed_style_knowledge(tmp_path)
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

    out_dir = tmp_path / "out"
    write_outputs(payload, out_dir, trace)
    style = (out_dir / "style.txt").read_text(encoding="utf-8")

    assert "128 BPM" in style
    assert any(x in style for x in ["EDM", "house", "dance pop", "future bass", "electropop"])


def test_style_changes_per_run_without_inheriting_previous_profile(tmp_path) -> None:
    _seed_style_knowledge(tmp_path)
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

    assert any(x in style_a for x in ["indie pop", "bedroom pop", "chill R&B", "lo-fi R&B"])
    assert "85 BPM" in style_a
    assert "traditional Chinese" not in style_a

    assert any(x in style_b for x in ["Chinese traditional", "ancient Chinese", "neoclassical Chinese", "Chinese folk"])
    assert "72 BPM" in style_b
    assert "indie pop" not in style_b


def test_style_hard_compiles_profile_genre_bpm_mood_vocal_plus_creative(tmp_path) -> None:
    _seed_style_knowledge(tmp_path)
    payload = _payload()
    trace = {
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

    out_dir = tmp_path / "out"
    write_outputs(payload, out_dir, trace)
    style = (out_dir / "style.txt").read_text(encoding="utf-8").strip()
    parts = [x.strip() for x in style.split(",") if x.strip()]

    assert "85 BPM" in style
    assert len(parts) <= 6
    assert any(x in style for x in ["indie pop", "bedroom pop", "chill R&B", "lo-fi R&B"])


def test_exclude_fallback_defaults_when_empty(tmp_path) -> None:
    _seed_style_knowledge(tmp_path)
    payload = _payload()
    payload.exclude_tags = []
    trace = {"llm_calls": 1, "active_profile": "urban_introspective", "prosody_contract": {"bpm": 85}}
    out_dir = tmp_path / "out"
    write_outputs(payload, out_dir, trace)
    exclude = (out_dir / "exclude.txt").read_text(encoding="utf-8")
    assert "spoken" in exclude
    assert "talking" in exclude
    assert "noise" in exclude
    assert "acapella" in exclude
    assert "bad audio" in exclude
    assert "low quality" in exclude
