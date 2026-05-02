from __future__ import annotations
from ._review_prompts import POLISH
from .llm_runtime import call as llm_call


def _changed_lines(a: str, b: str) -> list[int]:
    x = [s for s in a.splitlines()]
    y = [s for s in b.splitlines()]
    n = max(len(x), len(y))
    return [i + 1 for i in range(n) if (x[i] if i < len(x) else "") != (y[i] if i < len(y) else "")]


def self_review(draft: dict[str, object], max_retries: int = 1) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    brief = draft.get("brief") if isinstance(draft.get("brief"), dict) else {}
    calls = []
    diffs = []
    cur = ""
    for _ in range(3):
        nxt, meta = llm_call(POLISH.format(brief=brief, lyrics=cur), temperature=0.3)
        calls.append(meta)
        nxt = nxt.strip() or cur
        diffs.append(_changed_lines(cur, nxt))
        if nxt == cur:
            break
        cur = nxt
    return {**dict(draft), "lyrics": cur, "review_skipped": False, "polish_passes": len(calls), "polish_diffs": diffs, "_llm_calls": calls}
