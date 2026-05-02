from __future__ import annotations

import json
from pathlib import Path
from ._golden_match import pick_golden


def select_corpus(index_path: Path, portrait: dict[str, object], limit: int = 100) -> list[dict[str, object]]:
    rows = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return []
    words = [str(portrait.get("genre_guess", "")), str(portrait.get("bpm_range", "")), str(portrait.get("vibe", ""))]
    q = " ".join(words).lower()
    scored: list[tuple[int, dict[str, object]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = f"{row.get('title','')} {row.get('summary_50chars','')} {' '.join(row.get('emotion_tags', []) or [])}".lower()
        score = sum(1 for t in q.split() if t and t in text)
        if "indie pop" in q and "slot01_indie_lazy" in str(row.get("id", "")):
            score += 3
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [r for s, r in scored if s > 0][:limit]
    if len(top) < min(limit, 80):
        top = [r for _, r in scored[:limit]]
    return top


def select_golden_anchors(pool: list[dict[str, object]], portrait: dict[str, object]) -> list[dict[str, object]]:
    picked, _ = pick_golden(pool, str(portrait.get("genre_guess", "")))
    return picked


def select_golden_anchors_with_mode(pool: list[dict[str, object]], portrait: dict[str, object]) -> tuple[list[dict[str, object]], str]:
    return pick_golden(pool, str(portrait.get("genre_guess", "")))
