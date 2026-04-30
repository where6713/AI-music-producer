from __future__ import annotations

import json
from pathlib import Path

from src.main import _derive_prosody_matrix_aligned
from src.producer_tools.self_check.gate_g7 import _pm_audit_checks
from src.schemas import LyricPayload


def _seed_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lyrics.txt").write_text("[Verse 1]\nline one\nline two\n", encoding="utf-8")
    (out_dir / "style.txt").write_text("ok\n", encoding="utf-8")
    (out_dir / "exclude.txt").write_text("ok\n", encoding="utf-8")
    (out_dir / "lyric_payload.json").write_text("{}\n", encoding="utf-8")
    (out_dir / "trace.json").write_text("{}\n", encoding="utf-8")
    (out_dir / "audit.md").write_text("## 0.\n## 1.\n## 2.\n## 3.\n## 4.\n", encoding="utf-8")


def _payload_with_lines() -> LyricPayload:
    return LyricPayload.model_validate(
        {
            "distillation": {
                "emotional_register": "restrained",
                "core_tension": "want but stop",
                "valence": "negative",
                "arousal": "medium",
                "forbidden_literal_phrases": [],
            },
            "structure": {
                "section_order": ["[Verse 1]", "[Chorus]", "[Verse 2]"],
                "hook_section": "[Chorus]",
                "hook_line_index": 1,
            },
            "lyrics_by_section": [
                {
                    "tag": "[Verse 1]",
                    "lines": [{"primary": "line one"}, {"primary": "line two"}],
                }
            ],
            "style_tags": {
                "genre": ["indie pop"],
                "mood": ["melancholic"],
                "instruments": ["soft piano"],
                "vocals": ["intimate vocals"],
                "production": ["lo-fi"],
            },
            "exclude_tags": ["EDM"],
            "variants": [
                {
                    "variant_id": "a",
                    "narrative_pov": "first_person",
                    "lyrics_by_section": [{"tag": "[Verse 1]", "lines": [{"primary": "line one"}]}],
                },
                {
                    "variant_id": "b",
                    "narrative_pov": "second_person",
                    "lyrics_by_section": [{"tag": "[Verse 1]", "lines": [{"primary": "line one"}]}],
                },
                {
                    "variant_id": "c",
                    "narrative_pov": "third_person",
                    "lyrics_by_section": [{"tag": "[Verse 1]", "lines": [{"primary": "line one"}]}],
                },
            ],
            "chosen_variant_id": "a",
        }
    )


def test_derive_prosody_aligned_false_when_r18_failed() -> None:
    payload = _payload_with_lines()
    lint_report = {"failed_rules": ["R18"]}
    trace = {"prosody_contract": {"verse_line_max": 9, "chorus_line_max": 7, "bridge_line_max": 13}}
    assert _derive_prosody_matrix_aligned(payload, lint_report, trace) is False


def test_pm_audit_prosody_check_fails_when_r18_present(tmp_path) -> None:
    _seed_outputs(tmp_path / "out")
    trace_payload = {
        "profile_source": "cli_override",
        "few_shot_source_ids": ["github:local/a.json#1", "github:local/b.json#2"],
        "lint_report": {
            "craft_score": 0.9,
            "is_dead": False,
            "failed_rules": ["R18"],
            "violations": [],
            "hard_kill_rules": [],
        },
        "prosody_contract": {
            "bpm": 72,
            "verse_line_min": 3,
            "verse_line_max": 9,
            "chorus_line_min": 3,
            "chorus_line_max": 7,
            "bridge_line_min": 3,
            "bridge_line_max": 13,
        },
    }
    checks = _pm_audit_checks(tmp_path, trace_payload, tmp_path / "out")
    assert checks["prosody_matrix_aligned"]["ok"] is False


def test_pm_audit_prosody_check_passes_when_r18_absent_and_outputs_exist(tmp_path) -> None:
    _seed_outputs(tmp_path / "out")
    trace_payload = {
        "profile_source": "cli_override",
        "few_shot_source_ids": ["github:local/a.json#1", "github:local/b.json#2"],
        "lint_report": {
            "craft_score": 0.9,
            "is_dead": False,
            "failed_rules": [],
            "violations": [],
            "hard_kill_rules": [],
        },
        "prosody_contract": {
            "bpm": 72,
            "verse_line_min": 3,
            "verse_line_max": 9,
            "chorus_line_min": 3,
            "chorus_line_max": 7,
            "bridge_line_min": 3,
            "bridge_line_max": 13,
        },
    }
    checks = _pm_audit_checks(tmp_path, trace_payload, tmp_path / "out")
    assert checks["prosody_matrix_aligned"]["ok"] is True
