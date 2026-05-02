from __future__ import annotations

import re
from pathlib import Path


def _tokens(text: str) -> set[str]:
    return {x for x in re.split(r"[\s,，]+", (text or "").strip().lower()) if x}


def style_tokens(path: str) -> set[str]:
    p = Path(path)
    if not p.exists() or p.suffix.lower() != ".txt":
        return set()
    try:
        for line in p.read_text(encoding="utf-8").splitlines()[:8]:
            if line.lower().startswith("# style:"):
                return _tokens(line.split(":", 1)[1])
    except Exception:
        return set()
    return set()


def pick_golden(pool: list[dict[str, object]], genre_guess: str) -> tuple[list[dict[str, object]], str]:
    genre = _tokens(genre_guess)
    uniq: dict[str, dict[str, object]] = {}
    for row in pool:
        sid = str(row.get("id", ""))
        if "golden_dozen" in sid and sid not in uniq:
            uniq[sid] = row
    matched = [sid for sid in uniq if style_tokens(sid) & genre]
    if matched:
        ids = sorted(matched)[:2]
        return [uniq[i] for i in ids], "matched"
    ids = sorted(uniq.keys())[:2]
    return [uniq[i] for i in ids], "fallback_global"
