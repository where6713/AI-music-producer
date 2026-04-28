from __future__ import annotations

import pytest

from src.main import (
    _apply_retrieval_profile_decision,
    _guard_targeted_revise_scope,
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
                        {"primary": "放下吧", "backing": "", "tail_pinyin": "", "char_count": 3},
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "放下吧", "backing": "", "tail_pinyin": "", "char_count": 3},
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


def test_guard_targeted_revise_scope_reverts_non_targeted_lines() -> None:
    original = _payload()
    revised = original.model_copy(deep=True)

    revised.lyrics_by_section[0].lines[0].primary = "门只掩着，我把手慢慢收回来"
    revised.lyrics_by_section[1].lines[0].primary = "把号码放下啊"

    lint_report = {
        "failed_rules": ["R01"],
        "violations": [
            {
                "rule": "R01",
                "detail": "hook line tail is not open-final with level tone",
                "section": "[Chorus]",
                "line": 1,
            }
        ],
    }

    _guard_targeted_revise_scope(original, revised, lint_report)

    assert revised.lyrics_by_section[0].lines[0].primary == original.lyrics_by_section[0].lines[0].primary
    assert revised.lyrics_by_section[1].lines[0].primary == "把号码放下啊"


def test_guard_targeted_revise_scope_is_noop_without_targeted_violations() -> None:
    original = _payload()
    revised = original.model_copy(deep=True)
    revised.lyrics_by_section[0].lines[0].primary = "门只掩着，我把手慢慢收回来"

    _guard_targeted_revise_scope(original, revised, {"failed_rules": ["R14"], "violations": []})

    assert revised.lyrics_by_section[0].lines[0].primary == "门只掩着，我把手慢慢收回来"


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
    payload.variants[0].lyrics_by_section = payload.lyrics_by_section
    payload.variants[1].lyrics_by_section = payload.lyrics_by_section
    payload.variants[2].lyrics_by_section = payload.lyrics_by_section

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

    def _fake_lint(_payload, **_kwargs):
        return {
            "pass": True,
            "failed_rules": [],
            "violations": [],
            "active_profile": "urban_introspective",
            "skipped_rules_by_profile": [],
            "profile_specific_violations": [],
            "is_dead": False,
            "death_reason": [],
            "hard_kill_rules": [],
            "hard_penalty_count": 0,
            "soft_penalty_count": 0,
            "penalty_score": 0,
            "craft_score": 0.9,
            "all_dead_run_status": "",
        }

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "lint_payload", _fake_lint)
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


def test_produce_verbose_prints_profile_source(tmp_path, monkeypatch, capsys) -> None:
    # R01 was downgraded to SOFT_PENALTY. The _payload() fixture has an R01 violation
    # (hook line tail "吧" is not open-final+level-tone), but with R01 as SOFT_PENALTY
    # the craft_score stays above 0.85, so dry-run succeeds and prints profile info.
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
            "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)

    # dry-run now returns exit 0 because R01 soft-penalty keeps craft_score >= 0.85
    main_mod.produce(
        raw_intent="分手后夜里想发消息又忍住",
        genre="",
        mood="",
        vocal="female",
        profile="urban_introspective",
        lang="zh-CN",
        out_dir=str(tmp_path / "out"),
        verbose=True,
        dry_run=True,
    )

    out = capsys.readouterr().out
    assert "active_profile=urban_introspective" in out
    assert "profile_source=cli_override" in out


def test_produce_dry_run_prints_generation_error_stage(tmp_path, monkeypatch, capsys) -> None:
    from src import main as main_mod

    def _raise_generate(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _raise_generate)

    with pytest.raises(Exception) as err:
        main_mod.produce(
            raw_intent="测试",
            genre="",
            mood="",
            vocal="any",
            profile="urban_introspective",
            lang="zh-CN",
            out_dir=str(tmp_path / "out"),
            verbose=False,
            dry_run=True,
        )

    assert getattr(err.value, "exit_code", None) == 2
    out = capsys.readouterr().out
    assert "run_status=REJECTED generation error" in out
    assert "error_stage=initial_generation" in out
    assert "error_type=ValueError" in out


def test_apply_retrieval_profile_decision_uses_router_active_profile_when_present() -> None:
    trace = {
        "active_profile": "uplift_pop",
        "profile_source": "genre_match",
        "few_shot_source_ids": ["lyric-up-001", "lyric-up-002", "lyric-up-003"],
        "retrieval_profile_vote": "",
        "retrieval_vote_confidence": 0.0,
        "retrieval_profile_source": "initial",
    }

    _apply_retrieval_profile_decision(trace)

    decision = trace.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["active_profile"] == "uplift_pop"
    assert decision["decision_reason"] == "activated"


def test_produce_rejects_when_all_variants_dead_after_targeted_revise(tmp_path, monkeypatch) -> None:
    from src import main as main_mod

    payload = _payload()
    # Force R03 HARD_KILL by adding a forbidden phrase that exists in lyrics
    payload.distillation.forbidden_literal_phrases = ["夜色还在窗沿徘徊"]
    dead_sections = [
        {
            "tag": "[Verse 1]",
            "voice_tags_inline": [],
            "lines": [
                        {"primary": "夜色还在窗沿徘徊", "backing": "", "tail_pinyin": "", "char_count": 8},
                        {"primary": "指尖悬在未发的对白", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "理智把冲动轻轻按开", "backing": "", "tail_pinyin": "", "char_count": 9},
                        {"primary": "放下吧", "backing": "", "tail_pinyin": "", "char_count": 3},
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "放下吧", "backing": "", "tail_pinyin": "", "char_count": 3},
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
    ]

    payload.lyrics_by_section = [type(payload.lyrics_by_section[0]).model_validate(x) for x in dead_sections]
    for variant in payload.variants:
        variant.lyrics_by_section = [type(payload.lyrics_by_section[0]).model_validate(x) for x in dead_sections]

    calls = {"n": 0}

    def _fake_generate(*_args, **_kwargs):
        calls["n"] += 1
        return payload.model_copy(deep=True), {
            "provider": "openai-compatible",
            "model_used": "gpt-5.3-codex",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "llm_calls": 1,
            "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    def _fail_write_outputs(*_args, **_kwargs):
        raise AssertionError("write_outputs should not be called when all variants are dead")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "write_outputs", _fail_write_outputs)

    with pytest.raises(Exception) as err:
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

    assert getattr(err.value, "exit_code", None) == 2
    assert calls["n"] == 2
    assert not (tmp_path / "out" / "lyrics.txt").exists()
    assert (tmp_path / "out" / "trace.json").exists()
    assert (tmp_path / "out" / "audit.md").exists()


def test_produce_rejects_when_postprocess_result_is_dead(tmp_path, monkeypatch) -> None:
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
            "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    def _fake_lint(_payload, **_kwargs):
        return {
            "pass": False,
            "failed_rules": ["R14"],
            "violations": [
                {
                    "rule": "R14",
                    "detail": "forbidden verb-object phrase: 收回来",
                    "section": "[Chorus]",
                    "line": 1,
                }
            ],
            "active_profile": "urban_introspective",
            "skipped_rules_by_profile": [],
            "profile_specific_violations": [],
            "is_dead": True,
            "death_reason": ["R14: forbidden verb-object phrase: 收回来"],
            "hard_kill_rules": ["R14"],
            "hard_penalty_count": 0,
            "soft_penalty_count": 0,
            "penalty_score": 0,
            "all_dead_run_status": "",
        }

    def _fail_write_outputs(*_args, **_kwargs):
        raise AssertionError("write_outputs should not be called when postprocess is dead")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "lint_payload", _fake_lint)
    monkeypatch.setattr(main_mod, "write_outputs", _fail_write_outputs)

    with pytest.raises(Exception) as err:
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

    assert getattr(err.value, "exit_code", None) == 2
    assert not (tmp_path / "out" / "lyrics.txt").exists()
    assert (tmp_path / "out" / "trace.json").exists()
    assert (tmp_path / "out" / "audit.md").exists()


def test_produce_fails_quality_floor_and_skips_lyrics_write(tmp_path, monkeypatch) -> None:
    from src import main as main_mod

    payload = _payload()
    payload.variants[0].lyrics_by_section = payload.lyrics_by_section
    payload.variants[1].lyrics_by_section = payload.lyrics_by_section
    payload.variants[2].lyrics_by_section = payload.lyrics_by_section

    calls = {"n": 0}

    def _fake_generate(*_args, **_kwargs):
        calls["n"] += 1
        return payload.model_copy(deep=True), {
            "provider": "openai-compatible",
            "model_used": "gpt-5.3-codex",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "llm_calls": 1,
            "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    def _fake_lint(_payload, **_kwargs):
        return {
            "pass": True,
            "failed_rules": ["R05"],
            "violations": [
                {
                    "rule": "R05",
                    "detail": "line length out of tolerance",
                    "section": "[Chorus]",
                    "line": 1,
                }
            ],
            "active_profile": "urban_introspective",
            "skipped_rules_by_profile": [],
            "profile_specific_violations": [],
            "is_dead": False,
            "death_reason": [],
            "hard_kill_rules": [],
            "hard_penalty_count": 0,
            "soft_penalty_count": 1,
            "penalty_score": 1,
            "craft_score": 0.7,
            "all_dead_run_status": "",
        }

    def _fail_write_outputs(*_args, **_kwargs):
        raise AssertionError("write_outputs should not be called on quality floor failure")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "lint_payload", _fake_lint)
    monkeypatch.setattr(main_mod, "write_outputs", _fail_write_outputs)

    with pytest.raises(Exception) as err:
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

    assert getattr(err.value, "exit_code", None) == 2
    assert calls["n"] == 2
    assert not (tmp_path / "out" / "lyrics.txt").exists()
    assert (tmp_path / "out" / "trace.json").exists()
    assert (tmp_path / "out" / "audit.md").exists()


def test_produce_revises_when_compile_raises_structural_incomplete(tmp_path, monkeypatch) -> None:
    from src import main as main_mod
    from src.compile import StructuralIncompleteError

    initial_payload = _payload()
    initial_payload.lyrics_by_section = [initial_payload.lyrics_by_section[0]]
    for variant in initial_payload.variants:
        variant.lyrics_by_section = [initial_payload.lyrics_by_section[0]]

    revised_payload = _payload()
    for variant in revised_payload.variants:
        variant.lyrics_by_section = revised_payload.lyrics_by_section

    observed: dict[str, object] = {"targeted_prompt": "", "generate_calls": 0, "write_calls": 0}

    def _fake_generate(_user_input, **kwargs):
        observed["generate_calls"] = int(observed["generate_calls"]) + 1
        targeted_prompt = kwargs.get("targeted_revise_prompt")
        if targeted_prompt:
            observed["targeted_prompt"] = targeted_prompt
            return revised_payload.model_copy(deep=True), {
                "provider": "openai-compatible",
                "model_used": "gpt-5.3-codex",
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                "llm_calls": 1,
                "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
                "retrieval_profile_vote": "urban_introspective",
                "retrieval_vote_confidence": 0.67,
                "stage": "revise",
            }
        return initial_payload.model_copy(deep=True), {
            "provider": "openai-compatible",
            "model_used": "gpt-5.3-codex",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "llm_calls": 1,
            "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    def _fake_lint(_payload, **_kwargs):
        return {
            "pass": True,
            "failed_rules": [],
            "violations": [],
            "active_profile": "urban_introspective",
            "skipped_rules_by_profile": [],
            "profile_specific_violations": [],
            "is_dead": False,
            "death_reason": [],
            "hard_kill_rules": [],
            "hard_penalty_count": 0,
            "soft_penalty_count": 0,
            "penalty_score": 0,
            "craft_score": 0.9,
            "all_dead_run_status": "",
        }

    def _fake_write_outputs(payload, _out_dir, _trace):
        observed["write_calls"] = int(observed["write_calls"]) + 1
        if len(payload.lyrics_by_section) == 1:
            raise StructuralIncompleteError("missing required section: Chorus with at least 5 lines")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "lint_payload", _fake_lint)
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

    assert observed["generate_calls"] == 2
    assert observed["write_calls"] == 2
    assert "下游要求 V/C/V/C/Bridge/C 中必须有 Verse 与 Chorus 各 >=1 段，每段 >=5 行" in str(observed["targeted_prompt"])
    assert observed["targeted_prompt"] == main_mod.STRUCTURAL_REVISE_PROMPT


def test_produce_uses_structural_revise_prompt_when_lint_r00(tmp_path, monkeypatch) -> None:
    from src import main as main_mod

    initial_payload = _payload()
    initial_payload.lyrics_by_section = []
    for variant in initial_payload.variants:
        variant.lyrics_by_section = []

    revised_payload = _payload()
    for variant in revised_payload.variants:
        variant.lyrics_by_section = revised_payload.lyrics_by_section

    observed: dict[str, object] = {"targeted_prompt": "", "generate_calls": 0, "write_calls": 0}

    def _fake_generate(_user_input, **kwargs):
        observed["generate_calls"] = int(observed["generate_calls"]) + 1
        targeted_prompt = kwargs.get("targeted_revise_prompt")
        if targeted_prompt:
            observed["targeted_prompt"] = targeted_prompt
            return revised_payload.model_copy(deep=True), {
                "provider": "openai-compatible",
                "model_used": "gpt-5.3-codex",
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                "llm_calls": 1,
                "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
                "retrieval_profile_vote": "urban_introspective",
                "retrieval_vote_confidence": 0.67,
                "stage": "revise",
            }
        return initial_payload.model_copy(deep=True), {
            "provider": "openai-compatible",
            "model_used": "gpt-5.3-codex",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "llm_calls": 1,
            "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
            "retrieval_profile_vote": "urban_introspective",
            "retrieval_vote_confidence": 0.67,
            "stage": "initial",
        }

    def _fake_lint(payload, **_kwargs):
        if not payload.lyrics_by_section:
            return {
                "pass": False,
                "failed_rules": ["R00"],
                "violations": [{"rule": "R00", "detail": "lyrics_by_section is empty", "section": "", "line": 0}],
                "active_profile": "urban_introspective",
                "skipped_rules_by_profile": [],
                "profile_specific_violations": [],
                "is_dead": False,
                "death_reason": [],
                "hard_kill_rules": [],
                "hard_penalty_count": 0,
                "soft_penalty_count": 0,
                "penalty_score": 0,
                "craft_score": 0.0,
                "all_dead_run_status": "",
            }
        return {
            "pass": True,
            "failed_rules": [],
            "violations": [],
            "active_profile": "urban_introspective",
            "skipped_rules_by_profile": [],
            "profile_specific_violations": [],
            "is_dead": False,
            "death_reason": [],
            "hard_kill_rules": [],
            "hard_penalty_count": 0,
            "soft_penalty_count": 0,
            "penalty_score": 0,
            "craft_score": 0.9,
            "all_dead_run_status": "",
        }

    def _fake_write_outputs(_payload, _out_dir, _trace):
        observed["write_calls"] = int(observed["write_calls"]) + 1

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _fake_generate)
    monkeypatch.setattr(main_mod, "lint_payload", _fake_lint)
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

    assert observed["generate_calls"] == 2
    assert observed["write_calls"] == 1
    assert observed["targeted_prompt"] == main_mod.STRUCTURAL_REVISE_PROMPT


def test_produce_fails_loud_with_trace_when_initial_generation_crashes(tmp_path, monkeypatch) -> None:
    from src import main as main_mod

    def _boom_generate(*_args, **_kwargs):
        raise KeyError("broken payload")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _boom_generate)

    with pytest.raises(Exception) as err:
        main_mod.produce(
            raw_intent="just write a 2-line haiku only, no verse no chorus",
            genre="",
            mood="",
            vocal="any",
            profile="",
            lang="en-US",
            out_dir=str(tmp_path / "out"),
            verbose=False,
            dry_run=False,
        )

    assert getattr(err.value, "exit_code", None) == 2
    assert not (tmp_path / "out" / "lyrics.txt").exists()
    assert (tmp_path / "out" / "trace.json").exists()
    assert (tmp_path / "out" / "audit.md").exists()


def test_produce_fails_loud_when_few_shot_quality_insufficient(tmp_path, monkeypatch) -> None:
    from src import main as main_mod
    from src.retriever import InsufficientQualityFewShotError

    def _bad_generate(*_args, **_kwargs):
        raise InsufficientQualityFewShotError("insufficient quality few-shot samples after pre-injection validation")

    monkeypatch.setattr(main_mod, "generate_lyric_payload", _bad_generate)

    with pytest.raises(Exception) as err:
        main_mod.produce(
            raw_intent="分手后夜里想发消息又忍住",
            genre="",
            mood="",
            vocal="female",
            profile="",
            lang="zh-CN",
            out_dir=str(tmp_path / "out"),
            verbose=False,
            dry_run=False,
        )

    assert getattr(err.value, "exit_code", None) == 2
    assert not (tmp_path / "out" / "lyrics.txt").exists()
    assert (tmp_path / "out" / "trace.json").exists()
    assert (tmp_path / "out" / "audit.md").exists()
