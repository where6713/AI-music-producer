from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas import UserInput


CORPUS_FILES = [
    "corpus/poetry_classical.json",
    "corpus/lyrics_modern_zh.json",
]


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


def retrieve_few_shot_examples(
    user_input: UserInput,
    *,
    repo_root: Path,
    top_k: int = 3,
) -> list[dict[str, Any]]:
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
        normalized.append(
            {
                "source_id": str(row.get("source_id", "")),
                "type": str(row.get("type", "modern_lyric")),
                "title": str(row.get("title", "")),
                "emotion_tags_matched": [str(x) for x in row.get("emotion_tags", [])[:4]],
                "content": str(row.get("content", "")),
            }
        )
    return normalized
