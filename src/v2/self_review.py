from __future__ import annotations

from ._quality_rules import check


def self_review(draft: dict[str, object], max_retries: int = 1) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    violations = check(lyrics)
    out = dict(draft)
    if not violations:
        out["review_notes"] = "passed"
        out["quality_gate_failed"] = False
        return out
    for _ in range(max_retries):
        lyrics = _try_fix(lyrics)
        violations = check(lyrics)
        if not violations:
            break
    out["lyrics"] = lyrics
    out["review_notes"] = "; ".join(violations) if violations else "fixed"
    out["quality_gate_failed"] = bool(violations)
    if violations:
        out["needs_rewrite"] = True
    return out


def _try_fix(text: str) -> str:
    text = text.replace("我把", "")
    text = text.replace("让天亮替我回答", "等天亮给出回答")
    text = text.replace("把晚安留给", "把问候留在")
    text = text.replace("city lights", "灯火")
    return text
