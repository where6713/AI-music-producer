from __future__ import annotations

import json
from pathlib import Path

from src import claude_client
from src.schemas import UserInput


def _payload_json() -> str:
    return json.dumps(
        {
            "schema_version": "v2.1",
            "model_used": "gpt-5.3-codex",
            "skill_used": "lyric-craftsman@v2.1",
            "few_shot_examples_used": [
                {
                    "source_id": "poem-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags_matched": ["nostalgia", "restraint"],
                },
                {
                    "source_id": "lyric-002",
                    "type": "modern_lyric",
                    "title": "雨夜",
                    "emotion_tags_matched": ["distance", "regret"],
                },
            ],
            "distillation": {
                "emotional_register": "restrained",
                "core_tension": "want to call but must stop",
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
                        {
                            "primary": "电车到站你没回头",
                            "backing": "",
                            "tail_pinyin": "tou2",
                            "char_count": 8,
                        }
                    ],
                },
                {
                    "tag": "[Chorus]",
                    "voice_tags_inline": [],
                    "lines": [
                        {
                            "primary": "把号码放下吧",
                            "backing": "",
                            "tail_pinyin": "ba1",
                            "char_count": 7,
                        }
                    ],
                },
            ],
            "variants": [
                {
                    "variant_id": "a",
                    "narrative_pov": "first_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 11, "failed_rules": ["R05"], "rank": 2},
                },
                {
                    "variant_id": "b",
                    "narrative_pov": "second_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 13, "failed_rules": [], "rank": 1},
                },
                {
                    "variant_id": "c",
                    "narrative_pov": "third_person",
                    "lyrics_by_section": [],
                    "lint_result": {"passed_rules": 10, "failed_rules": ["R02", "R05"], "rank": 3},
                },
            ],
            "chosen_variant_id": "b",
            "style_tags": {
                "genre": ["mandopop"],
                "mood": ["melancholic"],
                "instruments": ["soft keys"],
                "vocals": ["intimate female vocals"],
                "production": ["lo-fi warmth"],
            },
            "exclude_tags": ["autotune", "EDM"],
        },
        ensure_ascii=False,
    )


def _seed_min_corpus(repo_root: Path) -> None:
    corpus_dir = repo_root / "corpus"
    clean_dir = corpus_dir / "_clean"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    poetry_rows = [
        {
            "source_id": "poem-jys-001",
            "type": "classical_poem",
            "title": "静夜思",
            "emotion_tags": ["nostalgia", "restraint"],
            "profile_tag": "classical_restraint",
            "content": "举头望明月，低头思故乡，夜色慢慢凉。",
            "valence": "neutral",
            "learn_point": "使用留白与具象意象承载情绪",
            "do_not_copy": "不要复写原句与段落顺序",
        }
    ]
    lyric_rows = [
        {
            "source_id": "lyric-modern-101",
            "type": "modern_lyric",
            "title": "凌晨未发送",
            "emotion_tags": ["breakup", "late-night"],
            "profile_tag": "urban_introspective",
            "content": "对话框停在最后一句，指尖仍然悬着。",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "不要复写原句与段落顺序",
        },
        {
            "source_id": "lyric-modern-102",
            "type": "modern_lyric",
            "title": "不再拨通",
            "emotion_tags": ["distance", "regret"],
            "profile_tag": "urban_introspective",
            "content": "手在拨出前停住，呼吸也跟着发颤。",
            "valence": "negative",
            "learn_point": "保留克制语气并用动作推进情绪",
            "do_not_copy": "不要复写原句与段落顺序",
        },
    ]

    (corpus_dir / "poetry_classical.json").write_text(
        json.dumps(poetry_rows, ensure_ascii=False),
        encoding="utf-8",
    )
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(lyric_rows, ensure_ascii=False),
        encoding="utf-8",
    )
    (clean_dir / "poetry_classical.json").write_text(
        json.dumps(poetry_rows, ensure_ascii=False),
        encoding="utf-8",
    )
    (clean_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(lyric_rows, ensure_ascii=False),
        encoding="utf-8",
    )
    profiles_dir = repo_root / "src" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "registry.json").write_text(
        json.dumps(
            {
                "profiles": {
                    "urban_introspective": {
                        "display_name": "都市内省",
                        "typical_genres": ["都市流行", "mandopop"],
                        "typical_moods": ["克制释怀", "melancholic"],
                        "craft_focus": "具象化身体记账 + 场景锚定",
                    },
                    "classical_restraint": {
                        "display_name": "古风留白",
                        "typical_genres": ["古风"],
                        "typical_moods": ["空寂"],
                        "craft_focus": "意象并置 + 留白 + 典故克制",
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_resolve_provider_prefers_openai_compatible_without_anthropic() -> None:
    config = claude_client._resolve_provider_config(
        {
            "OPENAI_API_KEY": "key-openai",
            "OPENAI_BASE_URL": "https://code.ppchat.vip/v1",
            "OPENAI_MODEL": "gpt-5.3-codex",
            "MOONSHOT_API_KEY": "key-moonshot",
            "MOONSHOT_BASE_URL": "https://api.moonshot.cn/v1",
            "MOONSHOT_MODEL": "kimi-k2.6-code-preview",
        },
        default_model="claude-opus-4-1-20250805",
    )

    assert config.provider == "openai-compatible"
    assert config.model == "gpt-5.3-codex"


def test_generate_payload_uses_openai_compatible_path(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path
    _seed_min_corpus(repo_root)
    (repo_root / ".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=key-openai",
                "OPENAI_BASE_URL=https://code.ppchat.vip/v1",
                "OPENAI_MODEL=gpt-5.3-codex",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(claude_client, "_load_skill_text", lambda _root, active_profile="": "skill")

    def _fake_openai_call(*, config, skill_text, prompt):
        assert config.provider == "openai-compatible"
        assert skill_text == "skill"
        assert "Generate lyric_payload JSON only" in prompt["task"]
        assert "以下示例展示的是 craft 方法" in prompt["few_shot_system_instruction"]
        constraints = prompt.get("structure_hard_constraints", {})
        assert constraints.get("required_sections") == ["[Verse 1]", "[Chorus]"]
        assert constraints.get("min_lines_per_required_section") == 5
        assert constraints.get("forbid_empty_lyrics_by_section") is True
        assert constraints.get("forbid_code_generated_lyrics_fallback") is True
        assert all(str(x.get("do_not_copy", "")).strip() for x in prompt["few_shot_examples"])
        return _payload_json(), {"input_tokens": 123, "output_tokens": 456, "total_tokens": 579}

    monkeypatch.setattr(claude_client, "_call_openai_compatible", _fake_openai_call)

    payload, trace = claude_client.generate_lyric_payload(
        UserInput(raw_intent="失恋三个月想联系但知道不能"),
        repo_root=repo_root,
    )

    assert trace["provider"] == "openai-compatible"
    assert trace["model_used"] == "gpt-5.3-codex"
    assert trace["llm_calls"] == 1
    assert trace["usage"]["total_tokens"] == 579
    assert trace["retrieval_profile_vote"] == "urban_introspective"
    assert trace["retrieval_vote_confidence"] >= (2 / 3)
    assert len(payload.few_shot_examples_used) >= 2
    assert len(payload.variants) == 3
    assert payload.chosen_variant_id in {"a", "b", "c"}


def test_generate_payload_normalizes_non_schema_response(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path
    _seed_min_corpus(repo_root)
    (repo_root / ".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=key-openai",
                "OPENAI_BASE_URL=https://code.ppchat.vip/v1",
                "OPENAI_MODEL=gpt-5.3-codex",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_client, "_load_skill_text", lambda _root, active_profile="": "skill")

    raw_non_schema = json.dumps(
        {
            "language": "zh-CN",
            "genre_hint": "mandopop",
            "mood_hint": "melancholic",
            "vocal_gender_hint": "female",
            "emotional_core": "restrained regret",
            "structure_plan": ["[Verse 1]", "[Chorus]"],
            "lyrics": {
                "[Verse 1]": ["电车到站你没回头"],
                "[Chorus]": ["把号码放下吧"],
            },
            "style_tags": ["mandopop", "melancholic"],
            "exclude_tags": ["edm drop"],
        },
        ensure_ascii=False,
    )

    monkeypatch.setattr(
        claude_client,
        "_call_openai_compatible",
        lambda **_kwargs: (
            raw_non_schema,
            {"input_tokens": 20, "output_tokens": 30, "total_tokens": 50},
        ),
    )

    payload, trace = claude_client.generate_lyric_payload(
        UserInput(raw_intent="失恋三个月想联系但知道不能", genre_hint="mandopop", mood_hint="melancholic"),
        repo_root=repo_root,
    )

    assert trace["provider"] == "openai-compatible"
    assert trace["model_used"] == "gpt-5.3-codex"
    assert trace["retrieval_profile_vote"] == "urban_introspective"
    assert trace["retrieval_vote_confidence"] >= (2 / 3)
    assert len(payload.few_shot_examples_used) >= 2
    assert len(payload.variants) == 3
    assert payload.chosen_variant_id == "a"
    assert payload.style_tags.genre


def test_load_skill_text_appends_profile_fragment(tmp_path) -> None:
    skill_root = tmp_path / ".claude" / "skills" / "lyric-craftsman"
    fragments = skill_root / "fragments"
    fragments.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("core-skill", encoding="utf-8")
    (fragments / "urban_introspective.md").write_text("urban-fragment", encoding="utf-8")

    merged = claude_client._load_skill_text(tmp_path, active_profile="urban_introspective")
    assert "core-skill" in merged
    assert "urban-fragment" in merged


def test_generate_payload_includes_profile_trace_fields(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path
    _seed_min_corpus(repo_root)
    (repo_root / ".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=key-openai",
                "OPENAI_BASE_URL=https://code.ppchat.vip/v1",
                "OPENAI_MODEL=gpt-5.3-codex",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_client, "_load_skill_text", lambda _root, active_profile="": "skill")
    monkeypatch.setattr(
        claude_client,
        "_call_openai_compatible",
        lambda **_kwargs: (
            _payload_json(),
            {"input_tokens": 20, "output_tokens": 30, "total_tokens": 50},
        ),
    )

    _payload, trace = claude_client.generate_lyric_payload(
        UserInput(raw_intent="失恋三个月想联系但知道不能", profile_override="urban_introspective"),
        repo_root=repo_root,
    )

    assert trace["active_profile"] == "urban_introspective"
    assert trace["profile_source"] == "cli_override"
    assert "corpus_balance" in trace
    assert "corpus_monoculture_risk" in trace


def test_normalize_structure_falls_back_when_order_missing() -> None:
    structure = claude_client._normalize_structure({}, [])
    assert structure["section_order"] == ["[Verse 1]", "[Chorus]"]
    assert structure["hook_section"] == "[Chorus]"


def test_normalize_variants_skips_sections_without_tag_or_lines() -> None:
    variants, chosen = claude_client._normalize_variants(
        [
            {
                "variant_id": "a",
                "lyrics_by_section": [
                    {"lines": [{"primary": "x"}]},
                    {"tag": "[Verse 1]", "lines": [{"primary": "line 1"}]},
                ],
            }
        ],
        base_sections=[],
    )

    assert chosen == "a"
    assert variants[0]["lyrics_by_section"][0]["tag"] == "[Verse 1]"


def test_extract_base_sections_accepts_name_and_text_fields() -> None:
    rows = claude_client._extract_base_sections(
        {
            "lyrics_by_section": [
                {
                    "name": "Verse 1",
                    "lines": [{"text": "line one"}, {"line": "line two"}],
                },
                {
                    "section": "chorus",
                    "lines": ["line c1", "line c2"],
                },
            ]
        }
    )

    tags = [row["tag"] for row in rows]
    assert "[Verse 1]" in tags
    assert "[Chorus]" in tags
