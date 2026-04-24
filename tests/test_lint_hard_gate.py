from __future__ import annotations

import json

from src.lint import lint_payload
from src.schemas import LyricPayload


def _make_payload(*, chorus_line: str) -> LyricPayload:
    return LyricPayload.model_validate(
        {
            "schema_version": "v2.1",
            "model_used": "gpt-5.3-codex",
            "skill_used": "lyric-craftsman@v2.1",
            "few_shot_examples_used": [
                {
                    "source_id": "poem-jys-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags_matched": ["nostalgia", "restraint"],
                },
                {
                    "source_id": "lyric-modern-101",
                    "type": "modern_lyric",
                    "title": "凌晨未发送",
                    "emotion_tags_matched": ["breakup", "late-night"],
                },
            ],
            "distillation": {
                "emotional_register": "restrained",
                "core_tension": "want to text but stop",
                "valence": "negative",
                "arousal": "medium",
                "forbidden_literal_phrases": ["失恋三个月"],
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
                        {"primary": "夜色还在窗沿徘徊", "backing": "", "tail_pinyin": "", "char_count": 8},
                        {"primary": "指尖悬在未发的对白", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "理智把冲动轻轻按开", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "把号码放下吧", "backing": "", "tail_pinyin": "", "char_count": 6},
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": chorus_line, "backing": "", "tail_pinyin": "", "char_count": len(chorus_line)},
                        {"primary": "未寄出的月光沉在口袋", "backing": "", "tail_pinyin": "", "char_count": 10},
                        {"primary": "你听不见我学着离开", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "我把晚安留给未来", "backing": "", "tail_pinyin": "", "char_count": 8},
                    ],
                },
                {
                    "tag": "[Verse 2]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "旧站台风把名字吹散", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "消息框静得像一片海", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "我把想念折成空白", "backing": "", "tail_pinyin": "", "char_count": 8},
                        {"primary": "让黎明替我把门关", "backing": "", "tail_pinyin": "", "char_count": 8},
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
                "instruments": ["soft keys"],
                "vocals": ["female"],
                "production": ["minimal"],
            },
            "exclude_tags": ["EDM"],
        }
    )


def test_lint_marks_r14_phrase_as_dead() -> None:
    payload = _make_payload(chorus_line="我把想念折成静默")

    report = lint_payload(payload)

    assert report["is_dead"] is True
    assert "R14" in report["hard_kill_rules"]
    assert any("折成静默" in row for row in report["death_reason"])


def test_lint_marks_r03_forbidden_literal_as_dead() -> None:
    payload = _make_payload(chorus_line="我失恋三个月还在等你吧")

    report = lint_payload(payload)

    assert report["is_dead"] is True
    assert "R03" in report["hard_kill_rules"]


def test_lint_marks_r16_global_phrase_as_dead(tmp_path) -> None:
    payload = _make_payload(chorus_line="霓虹天空里我还在走")
    registry = tmp_path / "registry.json"
    global_rules = tmp_path / "global_rules.json"
    registry.write_text(
        json.dumps(
            {
                "profiles": {
                    "urban_introspective": {
                        "R15_concrete_density": {"enforced": False},
                        "R16_profile_forbidden": [],
                        "R17_first_person_ratio_max": 0.9,
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    global_rules.write_text(
        json.dumps({"global_always_forbidden": ["霓虹天空"]}, ensure_ascii=False),
        encoding="utf-8",
    )

    report = lint_payload(
        payload,
        trace={"active_profile": "urban_introspective"},
        profiles_registry_path=registry,
        global_rules_path=global_rules,
    )

    assert "R16" in report["failed_rules"]
    assert "R16_global" in report["hard_kill_rules"]
