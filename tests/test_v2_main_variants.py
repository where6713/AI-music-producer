from __future__ import annotations

from src.main import _apply_retrieval_profile_decision, _score_variants
from src.schemas import LyricPayload


def _payload() -> LyricPayload:
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
                "forbidden_literal_phrases": ["失恋三个月想联系但知道不能"],
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
                        {"primary": "把号码放下吧", "backing": "", "tail_pinyin": "", "char_count": 6},
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
                    "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 0},
                },
                {
                    "variant_id": "b",
                    "narrative_pov": "second_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 0},
                },
                {
                    "variant_id": "c",
                    "narrative_pov": "third_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 0, "failed_rules": [], "rank": 0},
                },
            ],
            "chosen_variant_id": "a",
            "style_tags": {
                "genre": ["mandopop"],
                "mood": ["melancholic"],
                "instruments": ["soft keys"],
                "vocals": ["intimate female vocals"],
                "production": ["lo-fi warmth"],
            },
            "exclude_tags": ["autotune", "EDM"],
        }
    )


def test_score_variants_assigns_rank_and_chosen() -> None:
    payload = _payload()
    payload.variants[0].lyrics_by_section = payload.lyrics_by_section
    payload.variants[1].lyrics_by_section = payload.lyrics_by_section
    payload.variants[2].lyrics_by_section = payload.lyrics_by_section

    out, evidence = _score_variants(payload)
    assert out.chosen_variant_id in {"a", "b", "c"}
    assert len(evidence["ranking"]) == 3
    ranks = [v.lint_result.rank for v in out.variants]
    assert sorted(ranks) == [1, 2, 3]


def test_apply_retrieval_profile_decision_activates_when_vote_confident() -> None:
    trace = {
        "few_shot_source_ids": ["poem-jys-001", "lyric-modern-101", "lyric-modern-102"],
        "retrieval_profile_vote": "urban_introspective",
        "retrieval_vote_confidence": 2 / 3,
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["active_profile"] == "urban_introspective"
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["vote_confidence"] >= (2 / 3)
    assert decision["source_ids"] == ["poem-jys-001", "lyric-modern-101", "lyric-modern-102"]
