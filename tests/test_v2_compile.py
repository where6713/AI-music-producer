from __future__ import annotations

import json

from src.compile import write_outputs
from src.schemas import LyricPayload


def _payload() -> LyricPayload:
    return LyricPayload.model_validate(
        {
            "distillation": {
                "emotional_register": "restrained",
                "core_tension": "conflict",
                "valence": "negative",
                "arousal": "medium",
                "forbidden_literal_phrases": [],
            },
            "structure": {
                "section_order": ["[Verse 1]", "[Chorus]"],
                "hook_section": "[Chorus]",
                "hook_line_index": 1,
            },
            "lyrics_by_section": [
                {
                    "tag": "[Verse 1]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "车门合上灯影在晃", "backing": "", "tail_pinyin": "huang4", "char_count": 9}
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "把号码放下吧", "backing": "oh", "tail_pinyin": "ba1", "char_count": 7}
                    ],
                },
            ],
            "style_tags": {
                "genre": ["lo-fi r&b"],
                "mood": ["melancholic"],
                "instruments": ["soft keys"],
                "vocals": ["intimate male vocals"],
                "production": ["lo-fi warmth"],
            },
            "exclude_tags": ["autotune", "EDM"],
        }
    )


def test_compile_writes_triplet_and_payload(tmp_path) -> None:
    payload = _payload()
    trace = {"llm_calls": 1}
    write_outputs(payload, tmp_path, trace)

    assert (tmp_path / "lyrics.txt").exists()
    assert (tmp_path / "style.txt").exists()
    assert (tmp_path / "exclude.txt").exists()
    assert (tmp_path / "lyric_payload.json").exists()
    assert (tmp_path / "trace.json").exists()

    trace_loaded = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    assert trace_loaded["llm_calls"] == 1


def test_compile_backfills_retrieval_decision_block(tmp_path) -> None:
    payload = _payload()
    trace = {
        "llm_calls": 2,
        "few_shot_source_ids": ["lyric-modern-101", "poem-jys-001"],
        "retrieval_profile_vote": "urban_introspective",
        "retrieval_vote_confidence": 0.8,
        "retrieval_profile_source": "revise",
    }

    write_outputs(payload, tmp_path, trace)

    trace_loaded = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    decision = trace_loaded.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["active_profile"] == "urban_introspective"
    assert decision["decision_reason"] == "activated"
    assert decision["source_stage"] == "revise"
    assert decision["source_ids"] == ["lyric-modern-101", "poem-jys-001"]
