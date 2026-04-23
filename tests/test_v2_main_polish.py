from __future__ import annotations

from src.main import _force_hook_line_pass
from src.schemas import LyricPayload


def test_force_hook_line_pass_rewrites_chorus_tail() -> None:
    payload = LyricPayload.model_validate(
        {
            "schema_version": "v2.1",
            "model_used": "gpt-5.3-codex",
            "skill_used": "lyric-craftsman@v2.1",
            "few_shot_examples_used": [
                {
                    "source_id": "poem-jys-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags_matched": ["nostalgia"],
                },
                {
                    "source_id": "lyric-modern-101",
                    "type": "modern_lyric",
                    "title": "凌晨未发送",
                    "emotion_tags_matched": ["breakup"],
                },
            ],
            "distillation": {
                "emotional_register": "restrained",
                "core_tension": "want to text but stop",
                "valence": "negative",
                "arousal": "medium",
                "forbidden_literal_phrases": ["分手三个月"],
            },
            "structure": {
                "section_order": ["[Verse 1]", "[Chorus]", "[Verse 2]"],
                "hook_section": "[Chorus]",
                "hook_line_index": 1,
            },
            "lyrics_by_section": [
                {
                    "tag": "[Verse 1]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "凌晨风把窗帘吹开", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "旧对话还停在那一排", "backing": "", "tail_pinyin": "", "char_count": 10},
                        {"primary": "掌心烫得像要失态", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "最后把冲动慢慢按下", "backing": "", "tail_pinyin": "", "char_count": 10},
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "别让这一夜再回答", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "怕一开口就往回塌", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "把未寄出的句子都删吧", "backing": "", "tail_pinyin": "", "char_count": 10},
                        {"primary": "等天亮教我沉默吧", "backing": "", "tail_pinyin": "", "char_count": 8},
                    ],
                },
                {
                    "tag": "[Verse 2]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "路灯在雨里有点发白", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "心事绕回胸口成海", "backing": "", "tail_pinyin": "", "char_count": 8},
                        {"primary": "每次想靠近都折返", "backing": "", "tail_pinyin": "", "char_count": 8},
                        {"primary": "把你的名字留给晚", "backing": "", "tail_pinyin": "", "char_count": 8},
                    ],
                },
            ],
            "variants": [
                {
                    "variant_id": "a",
                    "narrative_pov": "first_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 1},
                },
                {
                    "variant_id": "b",
                    "narrative_pov": "second_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 2},
                },
                {
                    "variant_id": "c",
                    "narrative_pov": "third_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 3},
                },
            ],
            "chosen_variant_id": "a",
            "style_tags": {
                "genre": ["mandopop"],
                "mood": ["melancholic"],
                "instruments": ["piano"],
                "vocals": ["female"],
                "production": ["minimal"],
            },
            "exclude_tags": ["EDM"],
        }
    )

    assert _force_hook_line_pass(payload)
    chorus = payload.lyrics_by_section[1]
    assert chorus.lines[0].primary == "今夜把心事轻轻放下吧"
