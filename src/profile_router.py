from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas import UserInput


class AmbiguousProfileError(RuntimeError):
    def __init__(self, candidates: list[dict[str, str]]) -> None:
        super().__init__("ambiguous profile")
        self.candidates = candidates


class OverrideConflictError(RuntimeError):
    def __init__(self, *, override: str, vote_profile: str, confidence: float) -> None:
        message = (
            "override-vote conflict blocked: "
            f"override={override} vote_profile={vote_profile} confidence={confidence:.2f}. "
            "Action: confirm override or rerun without --profile."
        )
        super().__init__(message)
        self.override = override
        self.vote_profile = vote_profile
        self.confidence = confidence


def _norm(value: str) -> str:
    return value.strip().lower()


def _load_registry(repo_root: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads((repo_root / "src/profiles/registry.json").read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    return {str(k): v for k, v in profiles.items() if isinstance(v, dict)}


def _candidate_list(registry: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for profile_id, data in registry.items():
        out.append(
            {
                "profile_id": profile_id,
                "display_name": str(data.get("display_name", "")),
                "craft_focus": str(data.get("craft_focus", "")),
            }
        )
    return out


def load_profile_typical_moods(repo_root: Path, profile_id: str) -> list[str]:
    registry = _load_registry(repo_root)
    profile = registry.get(profile_id, {})
    if not isinstance(profile, dict):
        return []
    raw = profile.get("typical_moods", [])
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def resolve_active_profile(
    user_input: UserInput,
    *,
    repo_root: Path,
    retrieval_vote: str,
    vote_confidence: float,
) -> tuple[str, str, float | None]:
    registry = _load_registry(repo_root)
    if not registry:
        raise AmbiguousProfileError([])

    if user_input.profile_override and user_input.profile_override in registry:
        vote = _norm(retrieval_vote)
        override = _norm(user_input.profile_override)
        if vote and vote in registry and vote != override and vote_confidence >= 0.7:
            raise OverrideConflictError(
                override=user_input.profile_override,
                vote_profile=vote,
                confidence=float(vote_confidence),
            )
        return user_input.profile_override, "cli_override", None

    genre_hint = _norm(user_input.genre_hint)
    if genre_hint:
        for profile_id, data in registry.items():
            genres = [_norm(str(x)) for x in data.get("typical_genres", [])]
            if genre_hint in genres:
                return profile_id, "genre_match", None

    vote = _norm(retrieval_vote)
    if vote and vote in registry and vote_confidence >= (2 / 3):
        return vote, "corpus_vote", float(vote_confidence)

    mood_hint = _norm(user_input.mood_hint)
    if mood_hint:
        for profile_id, data in registry.items():
            moods = [_norm(str(x)) for x in data.get("typical_moods", [])]
            if mood_hint in moods:
                return profile_id, "mood_inference", None

    raise AmbiguousProfileError(_candidate_list(registry))
