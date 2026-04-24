from __future__ import annotations

import json

import pytest

from src.compile import StructuralIncompleteError, write_outputs
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
                        {"primary": "车门合上灯影在晃", "backing": "", "tail_pinyin": "huang4", "char_count": 9},
                        {"primary": "站台风把衣角又拉长", "backing": "", "tail_pinyin": "chang2", "char_count": 9},
                        {"primary": "屏幕停在未发的那行", "backing": "", "tail_pinyin": "hang2", "char_count": 9},
                        {"primary": "呼吸在指尖反复回放", "backing": "", "tail_pinyin": "fang4", "char_count": 9},
                        {"primary": "我把冲动轻轻按在掌", "backing": "", "tail_pinyin": "zhang3", "char_count": 9},
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {"primary": "把号码放下吧", "backing": "oh", "tail_pinyin": "ba1", "char_count": 7},
                        {"primary": "夜色把回声慢慢拉长", "backing": "", "tail_pinyin": "chang2", "char_count": 9},
                        {"primary": "我学着把晚安留给远方", "backing": "", "tail_pinyin": "fang1", "char_count": 10},
                        {"primary": "消息框在掌心轻轻发烫", "backing": "", "tail_pinyin": "tang4", "char_count": 10},
                        {"primary": "沉默比想念还更漫长", "backing": "", "tail_pinyin": "chang2", "char_count": 9},
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
    assert (tmp_path / "audit.md").exists()

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


def test_compile_infers_active_decision_when_vote_missing(tmp_path) -> None:
    payload = _payload()
    trace = {
        "llm_calls": 2,
        "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
        "retrieval_profile_vote": "",
        "retrieval_vote_confidence": 0.0,
        "retrieval_profile_source": "revise",
    }

    write_outputs(payload, tmp_path, trace)

    trace_loaded = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    decision = trace_loaded.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["vote_confidence"] >= (2 / 3)
    assert decision["active_profile"] == "urban_introspective"
    assert decision["decision_reason"] == "activated"


def test_compile_enriches_existing_inactive_decision_block(tmp_path) -> None:
    payload = _payload()
    trace = {
        "llm_calls": 2,
        "few_shot_source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
        "retrieval_profile_source": "revise",
        "retrieval_profile_decision": {
            "profile_vote": "",
            "vote_confidence": 0.0,
            "active_profile": "",
            "decision_reason": "no_profile_vote",
            "source_stage": "revise",
            "source_ids": ["lyric-modern-101", "lyric-modern-102", "poem-jys-001"],
        },
    }

    write_outputs(payload, tmp_path, trace)

    trace_loaded = json.loads((tmp_path / "trace.json").read_text(encoding="utf-8"))
    decision = trace_loaded.get("retrieval_profile_decision")
    assert isinstance(decision, dict)
    assert decision["profile_vote"] == "urban_introspective"
    assert decision["vote_confidence"] >= (2 / 3)
    assert decision["active_profile"] == "urban_introspective"
    assert decision["decision_reason"] == "activated"


def test_compile_writes_profile_decision_section_in_audit(tmp_path) -> None:
    payload = _payload()
    trace = {
        "llm_calls": 1,
        "active_profile": "urban_introspective",
        "profile_source": "cli_override",
        "profile_vote_confidence": None,
        "lint_report": {
            "skipped_rules_by_profile": ["R15"],
        },
    }

    write_outputs(payload, tmp_path, trace)

    audit = (tmp_path / "audit.md").read_text(encoding="utf-8")
    assert "## 0. Profile 决策" in audit
    assert "active_profile: urban_introspective" in audit
    assert "profile_source: cli_override" in audit
    assert "skipped_rules_by_profile: R15" in audit


def test_compile_audit_includes_profile_vote_counts_and_warning(tmp_path) -> None:
    payload = _payload()
    trace = {
        "llm_calls": 1,
        "active_profile": "uplift_pop",
        "profile_source": "corpus_vote",
        "profile_vote_confidence": 0.4,
        "retrieval_profile_vote_counts": {
            "uplift_pop": 1,
            "urban_introspective": 2,
        },
        "profile_routing_warnings": [
            "profile_routing_low_confidence profile=uplift_pop source=corpus_vote vote_confidence=0.40"
        ],
        "few_shot_examples": [
            {
                "source_id": "lyric-modern-101",
                "content_preview": "对话框停在最后一句，指尖仍然悬着。"[:30],
                "learn_point": "保留克制语气并用动作推进情绪",
                "do_not_copy": "不要复写原句与段落顺序",
            }
        ],
        "lint_report": {"skipped_rules_by_profile": []},
    }

    write_outputs(payload, tmp_path, trace)

    audit = (tmp_path / "audit.md").read_text(encoding="utf-8")
    assert "vote_confidence: 0.4" in audit
    assert "profile_vote_counts:" in audit
    assert "uplift_pop:1" in audit
    assert "urban_introspective:2" in audit
    assert "profile_routing_low_confidence" in audit
    assert "## 1. Few-shot 来源透明化" in audit
    assert "source_id=lyric-modern-101" in audit
    assert "learn_point=保留克制语气并用动作推进情绪" in audit
    assert "do_not_copy=不要复写原句与段落顺序" in audit


def test_compile_raises_structural_incomplete_without_chorus(tmp_path) -> None:
    payload = _payload()
    payload.lyrics_by_section = [payload.lyrics_by_section[0]]
    trace = {"llm_calls": 1}

    with pytest.raises(StructuralIncompleteError) as err:
        write_outputs(payload, tmp_path, trace)

    assert "missing required section" in str(err.value)


def test_compile_records_structure_counts_in_trace(tmp_path) -> None:
    payload = _payload()
    trace = {"llm_calls": 1}
    write_outputs(payload, tmp_path, trace)

    assert trace["compile_structure"]["verse_sections"] >= 1
    assert trace["compile_structure"]["chorus_sections"] >= 1
    assert trace["compile_structure"]["structural_ready"] is True
