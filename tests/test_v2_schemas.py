from __future__ import annotations

import pytest

from src.schemas import LyricPayload


def _valid_payload_dict() -> dict[str, object]:
    return {
        "distillation": {
            "emotional_register": "restrained",
            "core_tension": "want to reach out but must stop",
            "valence": "negative",
            "arousal": "medium",
            "forbidden_literal_phrases": ["失恋三个月", "想联系但知道不能"],
        },
        "structure": {
            "section_order": ["[Verse 1]", "[Chorus]", "[Verse 2]", "[Bridge]", "[Outro]"],
            "hook_section": "[Chorus]",
            "hook_line_index": 1,
        },
        "lyrics_by_section": [
            {
                "tag": "[Verse 1]",
                "voice_tags_inline": [],
                "lines": [
                    {"primary": "地铁门关上灯影在晃", "backing": "", "tail_pinyin": "huang4", "char_count": 10}
                ],
            },
            {
                "tag": "[Chorus]",
                "voice_tags_inline": ["[Soft]"],
                "lines": [
                    {"primary": "把号码放下吧", "backing": "", "tail_pinyin": "ba1", "char_count": 7}
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


def test_payload_schema_valid() -> None:
    payload = LyricPayload.model_validate(_valid_payload_dict())
    assert payload.schema_version == "v2.0"
    assert payload.skill_used == "lyric-craftsman@v1.0"


def test_payload_schema_invalid() -> None:
    bad = _valid_payload_dict()
    bad["distillation"] = {"emotional_register": "x"}
    with pytest.raises(Exception):
        LyricPayload.model_validate(bad)
