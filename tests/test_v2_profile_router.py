from __future__ import annotations

import json

import pytest

from src.profile_router import (
    AmbiguousProfileError,
    load_profile_typical_moods,
    resolve_active_profile,
)
from src.schemas import UserInput


def _seed_registry(tmp_path) -> None:
    profiles_dir = tmp_path / "src" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "registry.json").write_text(
        json.dumps(
            {
                "profiles": {
                    "urban_introspective": {
                        "display_name": "都市内省",
                        "typical_genres": ["都市流行"],
                        "typical_moods": ["克制释怀"],
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
            indent=2,
        ),
        encoding="utf-8",
    )


def test_profile_router_prefers_cli_override(tmp_path) -> None:
    _seed_registry(tmp_path)
    user_input = UserInput(
        raw_intent="想写一首古风留白",
        genre_hint="都市流行",
        mood_hint="克制释怀",
        profile_override="classical_restraint",
    )

    active_profile, source, vote_confidence = resolve_active_profile(
        user_input,
        repo_root=tmp_path,
        retrieval_vote="urban_introspective",
        vote_confidence=1.0,
    )

    assert active_profile == "classical_restraint"
    assert source == "cli_override"
    assert vote_confidence is None


def test_profile_router_uses_corpus_vote_when_confident(tmp_path) -> None:
    _seed_registry(tmp_path)
    user_input = UserInput(raw_intent="想写一首夜里克制的歌")

    active_profile, source, vote_confidence = resolve_active_profile(
        user_input,
        repo_root=tmp_path,
        retrieval_vote="urban_introspective",
        vote_confidence=2 / 3,
    )

    assert active_profile == "urban_introspective"
    assert source == "corpus_vote"
    assert vote_confidence >= (2 / 3)


def test_profile_router_uses_genre_before_corpus_vote(tmp_path) -> None:
    _seed_registry(tmp_path)
    user_input = UserInput(raw_intent="想写一首古风", genre_hint="古风")

    active_profile, source, vote_confidence = resolve_active_profile(
        user_input,
        repo_root=tmp_path,
        retrieval_vote="urban_introspective",
        vote_confidence=1.0,
    )

    assert active_profile == "classical_restraint"
    assert source == "genre_match"
    assert vote_confidence is None


def test_profile_router_uses_mood_when_vote_not_confident(tmp_path) -> None:
    _seed_registry(tmp_path)
    user_input = UserInput(raw_intent="写一首空寂的歌", mood_hint="空寂")

    active_profile, source, vote_confidence = resolve_active_profile(
        user_input,
        repo_root=tmp_path,
        retrieval_vote="urban_introspective",
        vote_confidence=0.5,
    )

    assert active_profile == "classical_restraint"
    assert source == "mood_inference"
    assert vote_confidence is None


def test_profile_router_raises_ambiguous_with_candidates(tmp_path) -> None:
    _seed_registry(tmp_path)
    user_input = UserInput(raw_intent="写点东西")

    with pytest.raises(AmbiguousProfileError) as err:
        resolve_active_profile(
            user_input,
            repo_root=tmp_path,
            retrieval_vote="",
            vote_confidence=0.0,
        )

    assert len(err.value.candidates) >= 2
    assert all("profile_id" in row for row in err.value.candidates)


def test_load_profile_typical_moods_returns_registry_values(tmp_path) -> None:
    _seed_registry(tmp_path)
    moods = load_profile_typical_moods(tmp_path, "urban_introspective")
    assert "克制释怀" in moods
