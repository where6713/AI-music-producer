from __future__ import annotations

import os
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


def _repo_golden_files() -> list[str]:
    root = Path(__file__).resolve().parents[2] / "corpus" / "golden_dozen"
    return [str(p) for p in sorted(root.glob("*.txt"))]


def _pick(uniq: dict[str, dict[str, object]], genre_guess: str) -> tuple[list[dict[str, object]], str]:
    genre = _tokens(genre_guess)
    matched = [sid for sid in uniq if style_tokens(sid) & genre]
    if matched:
        ids = sorted(set(matched))[:1]
        return [uniq[i] for i in ids], "matched"
    if not uniq:
        return [], "empty_pool"
    ids = sorted(set(uniq.keys()))[:1]
    return [uniq[i] for i in ids], "fallback_global"


def pick_golden(pool: list[dict[str, object]], genre_guess: str) -> tuple[list[dict[str, object]], str]:
    uniq: dict[str, dict[str, object]] = {}
    for row in pool:
        sid = str(row.get("id", ""))
        p = Path(sid)
        if p.suffix.lower() == ".txt" and p.exists() and sid not in uniq:
            uniq[sid] = row
    if uniq:
        return _pick(uniq, genre_guess)
    if os.getenv("V2_DISABLE_FS_FALLBACK") == "1":
        return [], "empty_pool"
    fs = {sid: {"id": sid} for sid in _repo_golden_files()}
    picked, mode = _pick(fs, genre_guess)
    return picked, "fallback_filesystem" if fs else mode
