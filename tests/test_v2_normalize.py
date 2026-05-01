from __future__ import annotations

from pathlib import Path

from src import claude_client
from src.schemas import UserInput


def _user_input() -> UserInput:
    return UserInput(
        raw_intent="test",
        language="zh-CN",
        genre_hint="",
        mood_hint="",
        vocal_gender_hint="any",
        profile_override="",
        ref_audio_path="",
    )


def _base_payload() -> dict:
    return {
        "few_shot_examples_used": [],
        "distillation": {
            "emotional_register": "restrained",
            "core_tension": "test",
            "valence": "negative",
            "arousal": "medium",
            "forbidden_literal_phrases": [],
        },
        "structure": {
            "section_order": ["[Verse 1]", "[Chorus]"],
            "hook_section": "[Chorus]",
            "hook_line_index": 1,
        },
        "variants": [
            {"variant_id": "a", "lyrics_by_section": [], "lint_result": {"rank": 2}},
            {"variant_id": "b", "lyrics_by_section": [], "lint_result": {"rank": 1}},
            {"variant_id": "c", "lyrics_by_section": [], "lint_result": {"rank": 3}},
        ],
        "style_tags": {"genre": [], "mood": [], "instruments": [], "vocals": [], "production": []},
        "exclude_tags": [],
    }


def _section_lines(prefix: str) -> list:
    return [
        {"tag": "[Verse 1]", "voice_tags_inline": [], "lines": [{"primary": f"{prefix} verse"}]},
        {"tag": "[Chorus]", "voice_tags_inline": [], "lines": [{"primary": f"{prefix} chorus"}]},
    ]


def test_variant_map_with_chosen_id() -> None:
    payload = _base_payload()
    payload["chosen_variant_id"] = "b"
    payload["lyrics_by_section"] = {
        "a": _section_lines("A"),
        "b": _section_lines("B"),
        "c": _section_lines("C"),
    }
    normalized, meta = claude_client._normalize_payload_dict_with_meta(
        payload,
        user_input=_user_input(),
        model_used="m",
        few_shot_examples=[],
        repo_root=Path.cwd(),
        active_profile="urban_introspective",
    )
    assert normalized["lyrics_by_section"][0]["lines"][0]["primary"].startswith("B")
    assert meta["normalize_branch"] == "variant_map_chosen"
    assert meta["chosen_variant_id_resolved"] == "b"
    assert meta["chosen_variant_id_source"] == "raw"


def test_variant_map_chosen_missing_uses_top1() -> None:
    payload = _base_payload()
    payload["lyrics_by_section"] = {
        "a": _section_lines("A"),
        "b": _section_lines("B"),
        "c": _section_lines("C"),
    }
    normalized, meta = claude_client._normalize_payload_dict_with_meta(
        payload,
        user_input=_user_input(),
        model_used="m",
        few_shot_examples=[],
        repo_root=Path.cwd(),
        active_profile="urban_introspective",
    )
    assert normalized["lyrics_by_section"][0]["lines"][0]["primary"].startswith("B")
    assert meta["normalize_branch"] == "variant_map_fallback_top1"
    assert meta["chosen_variant_id_resolved"] == "b"
    assert meta["chosen_variant_id_source"] == "lint_top1"


def test_variant_map_chosen_empty_falls_back() -> None:
    payload = _base_payload()
    payload["chosen_variant_id"] = "b"
    payload["lyrics_by_section"] = {
        "a": _section_lines("A"),
        "b": [],
        "c": _section_lines("C"),
    }
    normalized, meta = claude_client._normalize_payload_dict_with_meta(
        payload,
        user_input=_user_input(),
        model_used="m",
        few_shot_examples=[],
        repo_root=Path.cwd(),
        active_profile="urban_introspective",
    )
    assert normalized["lyrics_by_section"][0]["lines"][0]["primary"].startswith("A")
    assert meta["normalize_branch"] == "variant_map_fallback_first_nonempty"
    assert meta["chosen_variant_id_source"] == "first_nonempty"


def test_variant_map_all_empty_triggers_repair() -> None:
    payload = _base_payload()
    payload["chosen_variant_id"] = "b"
    payload["lyrics_by_section"] = {"a": [], "b": [], "c": []}
    normalized, meta = claude_client._normalize_payload_dict_with_meta(
        payload,
        user_input=_user_input(),
        model_used="m",
        few_shot_examples=[],
        repo_root=Path.cwd(),
        active_profile="urban_introspective",
    )
    assert normalized["lyrics_by_section"] == []
    assert meta["normalize_branch"] in {
        "variant_map_fallback_first_nonempty",
        "variant_map_fallback_top1",
        "variant_map_chosen",
    } or normalized["lyrics_by_section"] == []
