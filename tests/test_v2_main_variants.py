from __future__ import annotations

import pytest

from src.main import (
    _apply_retrieval_profile_decision,
    _merge_revise_trace_metadata,
    _score_variants,
)
from src.profile_router import AmbiguousProfileError
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
        "retrieval_profile_source": "initial",
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["active_profile"] == "urban_introspective"
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["vote_confidence"] >= (2 / 3)
    assert decision["source_ids"] == ["poem-jys-001", "lyric-modern-101", "lyric-modern-102"]
    assert decision["source_stage"] == "initial"


def test_apply_retrieval_profile_decision_marks_reason_when_not_active() -> None:
    trace = {
        "few_shot_source_ids": ["poem-jys-001", "lyric-modern-101"],
        "retrieval_profile_vote": "urban_introspective",
        "retrieval_vote_confidence": 0.5,
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["active_profile"] == ""
    assert decision["decision_reason"] == "insufficient_confidence"


def test_merge_revise_trace_metadata_prefers_revise_retrieval_fields() -> None:
    trace = {
        "retrieval_profile_vote": "classical_restraint",
        "retrieval_vote_confidence": 0.5,
        "few_shot_source_ids": ["poem-jys-001", "poem-cy-002"],
        "retrieval_profile_source": "initial",
    }
    revise_trace = {
        "retrieval_profile_vote": "urban_introspective",
        "retrieval_vote_confidence": 2 / 3,
        "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
    }

    _merge_revise_trace_metadata(trace, revise_trace)

    assert trace["retrieval_profile_vote"] == "urban_introspective"
    assert trace["retrieval_vote_confidence"] >= (2 / 3)
    assert trace["few_shot_source_ids"] == ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"]
    assert trace["retrieval_profile_source"] == "revise"


def test_merge_revise_trace_metadata_keeps_initial_when_revise_missing() -> None:
    trace = {
        "retrieval_profile_vote": "classical_restraint",
        "retrieval_vote_confidence": 2 / 3,
        "few_shot_source_ids": ["poem-jys-001", "poem-cy-002"],
        "retrieval_profile_source": "initial",
    }
    revise_trace = {
        "stage": "revise",
    }

    _merge_revise_trace_metadata(trace, revise_trace)

    assert trace["retrieval_profile_vote"] == "classical_restraint"
    assert trace["retrieval_vote_confidence"] >= (2 / 3)
    assert trace["few_shot_source_ids"] == ["poem-jys-001", "poem-cy-002"]
    assert trace["retrieval_profile_source"] == "initial"


def test_merge_revise_trace_metadata_sets_default_source_stage() -> None:
    trace = {
        "retrieval_profile_vote": "classical_restraint",
        "retrieval_vote_confidence": 2 / 3,
        "few_shot_source_ids": ["poem-jys-001", "poem-cy-002"],
    }
    revise_trace = {
        "stage": "revise",
    }

    _merge_revise_trace_metadata(trace, revise_trace)

    assert trace["retrieval_profile_source"] == "initial"


def test_apply_retrieval_profile_decision_marks_no_vote_when_profile_missing() -> None:
    trace = {
        "few_shot_source_ids": ["custom-1", "custom-2"],
        "retrieval_profile_vote": "",
        "retrieval_vote_confidence": 0.9,
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["active_profile"] == ""
    assert decision["decision_reason"] == "no_profile_vote"


def test_apply_retrieval_profile_decision_treats_missing_confidence_as_zero() -> None:
    trace = {
        "few_shot_source_ids": ["poem-jys-001", "lyric-modern-101"],
        "retrieval_profile_vote": "urban_introspective",
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["vote_confidence"] == 0.0
    assert decision["active_profile"] == ""
    assert decision["decision_reason"] == "insufficient_confidence"


def test_apply_retrieval_profile_decision_infers_profile_from_source_ids_when_vote_missing() -> None:
    trace = {
        "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
        "retrieval_profile_vote": "",
        "retrieval_vote_confidence": 2 / 3,
        "retrieval_profile_source": "revise",
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["active_profile"] == "urban_introspective"
    assert decision["decision_reason"] == "activated"
    assert decision["source_stage"] == "revise"


def test_apply_retrieval_profile_decision_infers_confidence_from_source_ids_when_missing() -> None:
    trace = {
        "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
        "retrieval_profile_vote": "",
        "retrieval_vote_confidence": 0.0,
        "retrieval_profile_source": "revise",
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["vote_confidence"] >= (2 / 3)
    assert decision["active_profile"] == "urban_introspective"


def test_produce_sets_active_profile_and_source_in_trace(tmp_path, monkeypatch) -> None:
    from src import main as main_mod
    from src.schemas import LyricPayload

    payload = LyricPayload.model_validate(
        {
            "schema_version": "v2.1",
            "model_used": "gpt-5.3-codex",
            "skill_used": "lyric-craftsman@v2.1",
            "few_shot_examples_used": [
                {
                    "source_id": "lyric-modern-101",
                    "type": "modern_lyric",
                    "title": "凌晨未发送",
                    "emotion_tags_matched": ["breakup"],
                },
                {
                    "source_id": "poem-jys-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags_matched": ["nostalgia"],
                },
            ],
            "distillation": {
                "emotional_register": "restrained",
                "core_tension": "want to text but stop",
                "valence": "negative",
                "arousal": "medium",
                "forbidden_literal_phrases": ["x"],
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
                "vocals": ["female"],
                "production": ["minimal"],
            },
            "exclude_tags": ["EDM"],
        }
    )

    def _fake_generate(*_args, **_kwargs):
        return payload.model_copy(deep=True), {
            "provider": "openai-compatible",
            "model_used": "gpt-5.3-codex",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "llm_calls": 1,
            "few_shot_source_ids": ["lyric-modern-101", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    captured: dict[str, object] = {}

    def _fake_write_outputs(_payload, _out_dir, trace):
        captured.update(trace)

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "write_outputs", _fake_write_outputs)

    main_mod.produce(
        raw_intent="分手后夜里想发消息又忍住",
        genre="",
        mood="",
        vocal="female",
        profile="urban_introspective",
        lang="zh-CN",
        out_dir=str(tmp_path / "out"),
        verbose=False,
        dry_run=False,
    )

    assert captured["active_profile"] == "urban_introspective"
    assert captured["profile_source"] == "cli_override"


def test_apply_retrieval_profile_decision_handles_invalid_confidence_value() -> None:
    trace = {
        "few_shot_source_ids": ["poem-jys-001", "lyric-modern-101"],
        "retrieval_profile_vote": "urban_introspective",
        "retrieval_vote_confidence": "not-a-number",
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["vote_confidence"] == 0.0
    assert decision["active_profile"] == ""
    assert decision["decision_reason"] == "insufficient_confidence"


def test_merge_revise_trace_metadata_ignores_invalid_revise_confidence() -> None:
    trace = {
        "retrieval_profile_vote": "classical_restraint",
        "retrieval_vote_confidence": 2 / 3,
        "few_shot_source_ids": ["poem-jys-001", "poem-cy-002"],
    }
    revise_trace = {
        "retrieval_profile_vote": "urban_introspective",
        "retrieval_vote_confidence": "bad-confidence",
    }

    _merge_revise_trace_metadata(trace, revise_trace)

    assert trace["retrieval_profile_vote"] == "urban_introspective"
    assert trace["retrieval_vote_confidence"] >= (2 / 3)


def test_produce_raises_ambiguous_profile_error(tmp_path, monkeypatch) -> None:
    from src import main as main_mod

    payload = _payload()
    payload.variants[0].lyrics_by_section = payload.lyrics_by_section
    payload.variants[1].lyrics_by_section = payload.lyrics_by_section
    payload.variants[2].lyrics_by_section = payload.lyrics_by_section

    def _fake_generate(*_args, **_kwargs):
        return payload.model_copy(deep=True), {
            "provider": "openai-compatible",
            "model_used": "gpt-5.3-codex",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "llm_calls": 1,
            "few_shot_source_ids": ["custom-1", "custom-2"],
            "retrieval_profile_vote": "",
            "retrieval_vote_confidence": 0.0,
            "stage": "initial",
        }

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)

    with pytest.raises(AmbiguousProfileError) as err:
        main_mod.produce(
            raw_intent="写点东西",
            genre="",
            mood="",
            vocal="any",
            profile="",
            lang="zh-CN",
            out_dir=str(tmp_path / "out"),
            verbose=False,
            dry_run=False,
        )

    assert "ambiguous profile" in str(err.value)
    assert len(err.value.candidates) >= 2
