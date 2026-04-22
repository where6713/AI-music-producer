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
    corpus_dir.mkdir(parents=True, exist_ok=True)
    (corpus_dir / "poetry_classical.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "poem-jys-001",
                    "type": "classical_poem",
                    "title": "静夜思",
                    "emotion_tags": ["nostalgia", "restraint"],
                    "profile_tag": "classical_restraint",
                    "content": "举头望明月，低头思故乡。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (corpus_dir / "lyrics_modern_zh.json").write_text(
        json.dumps(
            [
                {
                    "source_id": "lyric-modern-101",
                    "type": "modern_lyric",
                    "title": "凌晨未发送",
                    "emotion_tags": ["breakup", "late-night"],
                    "profile_tag": "urban_introspective",
                    "content": "对话框停在最后一句。",
                },
                {
                    "source_id": "lyric-modern-102",
                    "type": "modern_lyric",
                    "title": "不再拨通",
                    "emotion_tags": ["distance", "regret"],
                    "profile_tag": "urban_introspective",
                    "content": "手在拨出前停住。",
                },
            ],
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

    monkeypatch.setattr(claude_client, "_load_skill_text", lambda _root: "skill")

    def _fake_openai_call(*, config, skill_text, prompt):
        assert config.provider == "openai-compatible"
        assert skill_text == "skill"
        assert "Generate lyric_payload JSON only" in prompt["task"]
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
    monkeypatch.setattr(claude_client, "_load_skill_text", lambda _root: "skill")

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
