from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.schemas import UserInput


CORPUS_FILES = [
    "corpus/poetry_classical.json",
    "corpus/lyrics_modern_zh.json",
]

PROFILE_IDS = {
    "urban_introspective",
    "classical_restraint",
    "uplift_pop",
    "club_dance",
    "ambient_meditation",
}

MIN_PROFILE_COVERAGE = {
    "urban_introspective": 200,
    "classical_restraint": 200,
    "uplift_pop": 150,
    "club_dance": 100,
    "ambient_meditation": 80,
}


def _infer_profile_tag(row: dict[str, Any]) -> str:
    explicit = str(row.get("profile_tag", "")).strip()
    if explicit:
        return explicit

    row_type = str(row.get("type", "")).strip().lower()
    tags = [str(x).strip().lower() for x in row.get("emotion_tags", []) if str(x).strip()]

    if row_type == "modern_lyric":
        if any(x in tags for x in {"breakup", "late-night", "regret", "distance", "self-control"}):
            return "urban_introspective"
        return "urban_introspective"

    if row_type == "classical_poem":
        if any(x in tags for x in {"restraint", "nostalgia", "longing", "night", "separation"}):
            return "classical_restraint"
        return "classical_restraint"

    return ""


def _tokenize(text: str) -> list[str]:
    val = text.strip().lower()
    if not val:
        return []
    if any("\u4e00" <= ch <= "\u9fff" for ch in val):
        return [ch for ch in val if "\u4e00" <= ch <= "\u9fff"]
    return [x for x in val.replace(",", " ").replace(".", " ").split() if x]


def _load_corpus(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in CORPUS_FILES:
        fp = repo_root / rel
        if not fp.exists():
            continue
        payload = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            rows.extend([x for x in payload if isinstance(x, dict)])
    return rows


def _normalize_profile_confidence(row: dict[str, Any]) -> float:
    val = row.get("profile_confidence", 1.0)
    try:
        parsed = float(val)
    except (TypeError, ValueError):
        parsed = 1.0
    if parsed < 0.0:
        return 0.0
    if parsed > 1.0:
        return 1.0
    return parsed


def corpus_balance_check(repo_root: Path) -> dict[str, Any]:
    corpus = _load_corpus(repo_root)
    counts = {k: 0 for k in MIN_PROFILE_COVERAGE}
    for row in corpus:
        tag = _infer_profile_tag(row)
        if tag in counts:
            counts[tag] += 1

    warnings = []
    for profile_id, minimum in MIN_PROFILE_COVERAGE.items():
        current = counts.get(profile_id, 0)
        if current < minimum:
            warnings.append(
                f"profile={profile_id} current={current} minimum={minimum}"
            )

    return {
        "counts": counts,
        "minimum": dict(MIN_PROFILE_COVERAGE),
        "warnings": warnings,
    }


def retrieve_few_shot_examples(
    user_input: UserInput,
    *,
    repo_root: Path,
    top_k: int = 3,
    return_metadata: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    corpus = _load_corpus(repo_root)
    if not corpus:
        raise RuntimeError("few-shot corpus missing under corpus/")

    intent_tokens = set(_tokenize(user_input.raw_intent))
    hint_tokens = set(_tokenize(" ".join([user_input.genre_hint, user_input.mood_hint]).strip()))

    scored: list[tuple[int, dict[str, Any]]] = []
    for row in corpus:
        content = str(row.get("content", ""))
        title = str(row.get("title", ""))
        tags = row.get("emotion_tags", [])
        tags_text = " ".join([str(x) for x in tags])
        row_tokens = set(_tokenize(" ".join([title, content, tags_text])))
        score = len(intent_tokens & row_tokens) * 3 + len(hint_tokens & row_tokens)
        scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [row for _, row in scored[: max(2, min(top_k, 3))]]
    if len(selected) < 2:
        selected = [row for _, row in scored[:2]]

    normalized: list[dict[str, Any]] = []
    for row in selected:
        profile_tag = _infer_profile_tag(row)
        normalized.append(
            {
                "source_id": str(row.get("source_id", "")),
                "type": str(row.get("type", "modern_lyric")),
                "title": str(row.get("title", "")),
                "emotion_tags_matched": [str(x) for x in row.get("emotion_tags", [])[:4]],
                "profile_tag": profile_tag,
                "profile_confidence": _normalize_profile_confidence(row),
                "content": str(row.get("content", "")),
            }
        )

    if not return_metadata:
        return normalized

    votes = Counter(
        sample["profile_tag"]
        for sample in normalized
        if sample.get("profile_tag") in PROFILE_IDS
    )
    if votes:
        profile_vote, vote_count = votes.most_common(1)[0]
        vote_confidence = vote_count / max(len(normalized), 1)
    else:
        profile_vote = ""
        vote_confidence = 0.0

    monoculture_risk = (
        len(votes) == 1 and vote_confidence < 1.0 and len(normalized) >= 2
    )

    return {
        "samples": normalized,
        "profile_vote": profile_vote,
        "vote_confidence": vote_confidence,
        "corpus_balance": corpus_balance_check(repo_root),
        "corpus_monoculture_risk": monoculture_risk,
    }
