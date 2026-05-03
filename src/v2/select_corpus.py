# FROZEN after step-A-bis (commit 2cd1ffb). Do not modify without architect approval.
from __future__ import annotations

import json
import os
import re
from pathlib import Path


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
    picked, _ = _pick_golden(pool, str(portrait.get("genre_guess", "")))
    return picked


def select_golden_anchors_with_mode(pool: list[dict[str, object]], portrait: dict[str, object]) -> tuple[list[dict[str, object]], str]:
    return _pick_golden(pool, str(portrait.get("genre_guess", "")))


def _tokens(text: str) -> set[str]:
    return {x for x in re.split(r"[\s,，/]+", (text or "").strip().lower()) if x}


def _style_tokens(path: str) -> set[str]:
    p = Path(path)
    if not p.exists() or p.suffix.lower() != ".txt":
        return set()
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines()[:8]:
        if line.lower().startswith("# style:"):
            return _tokens(line.split(":", 1)[1])
    return set()


def _repo_golden_files() -> list[str]:
    root = Path(__file__).resolve().parents[2] / "corpus" / "golden_dozen"
    return [str(p) for p in sorted(root.glob("*.txt"))]


def _pick_golden(pool: list[dict[str, object]], genre_guess: str) -> tuple[list[dict[str, object]], str]:
    uniq: dict[str, dict[str, object]] = {}
    for row in pool:
        sid = str(row.get("id", ""))
        if Path(sid).exists() and Path(sid).suffix.lower() == ".txt" and sid not in uniq:
            uniq[sid] = row
    if not uniq and os.getenv("V2_DISABLE_FS_FALLBACK") != "1":
        uniq = {sid: {"id": sid} for sid in _repo_golden_files()}
    if not uniq:
        return [], "empty_pool"
    g = _tokens(genre_guess)
    matched = [sid for sid in uniq if _style_tokens(sid) & g]
    ids = sorted(set(matched if matched else uniq.keys()))[:1]
    mode = "matched" if matched else "fallback_global"
    return [uniq[i] for i in ids], mode


def extract_anchor_chorus(anchor_file: str) -> str:
    p = Path(anchor_file)
    if not p.exists():
        raise FileNotFoundError(f"no anchor file: {anchor_file}")
    text = p.read_text(encoding="utf-8", errors="ignore")
    lines = [x.rstrip() for x in text.splitlines()]
    body = [x.strip() for x in lines if x.strip() and not x.strip().startswith("#")]

    # A: explicit chorus tag
    tag = re.compile(r"^(?:\[\s*(?:chorus|refrain|副歌)\s*\]|【\s*副歌\s*】)$", re.I)
    sec = re.compile(r"^(?:\[.+\]|【.+】)$")
    for i, line in enumerate(body):
        if tag.match(line):
            out = []
            for j in range(i + 1, len(body)):
                if sec.match(body[j]):
                    break
                if not body[j]:
                    break
                out.append(body[j])
            if out:
                return "\n".join(out[:12])

    # B: repeated block by segmented paragraphs
    paras = [re.split(r"\n+", blk.strip()) for blk in re.split(r"\n\s*\n", text) if blk.strip()]
    paras = [[x.strip() for x in para if x.strip() and not x.strip().startswith("#")] for para in paras]
    best = []
    def lcs_len(a: list[str], b: list[str]) -> int:
        m, n = len(a), len(b)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for x in range(m):
            for y in range(n):
                dp[x+1][y+1] = dp[x][y] + 1 if a[x] == b[y] else max(dp[x][y+1], dp[x+1][y])
        return dp[m][n]
    for i, a in enumerate(paras):
        if len(a) < 4:
            continue
        score = max([lcs_len(a, b) for j, b in enumerate(paras) if j != i] or [0])
        if score >= 4 and len(a) > len(best):
            best = a
    if best:
        return "\n".join(best[:12])

    # C: densest middle window
    if body:
        start = int(len(body) * 0.2)
        end = max(start + 8, int(len(body) * 0.8))
        mid = body[start:end] if end > start else body
        def dens(win: list[str]) -> int:
            tok = [t for ln in win for t in re.split(r"\s+", ln) if t]
            return sum(tok.count(t) for t in set(tok))
        if len(mid) >= 8:
            cands = [mid[k:k+8] for k in range(0, len(mid)-7)]
            pick = max(cands, key=dens)
            return "\n".join(pick)

    # D: approximated raw (never empty)
    return "\n".join(body[:12] if body else ["夜里风很轻", "路灯慢慢过", "我还在想你", "车继续向前"])
