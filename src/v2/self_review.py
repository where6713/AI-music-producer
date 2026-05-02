from __future__ import annotations
from ._quality_rules import check
from ._review_prompts import PROMPT, SURGICAL
from .llm_runtime import call as llm_call

def _extra(text: str) -> list[str]:
    props = sum(text.count(x) for x in ["车", "路", "灯", "雨", "烟", "酒"])
    inv = text.count("把") + text.count("将") + text.count("替")
    return (["imagery_stack"] if props > 6 else []) + (["inversion_overload"] if inv > 4 else [])

def self_review(draft: dict[str, object], max_retries: int = 2) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    hard, soft = check(lyrics)
    violations = hard + _extra(lyrics)
    out = dict(draft)
    if not violations:
        return {**out, "review_notes": "passed", "quality_gate_failed": False, "retry_count": 0, "retry_modes": [], "failure_reasons": [], "_llm_calls": []}
    retry_count, llm_calls_meta, modes = 0, [], []
    for mode_prompt in [PROMPT, SURGICAL]:
        if retry_count >= max_retries:
            break
        retry_count += 1
        modes.append("full_revise" if retry_count == 1 else "surgical_fix")
        content, meta = llm_call(mode_prompt.format(lyrics=lyrics, violations="; ".join(violations)), temperature=0.3)
        llm_calls_meta.append(meta)
        lyrics = content.strip()
        hard, soft = check(lyrics)
        violations = hard + _extra(lyrics)
        if not violations:
            break
    return {**out, "lyrics": lyrics, "review_notes": "; ".join(violations) if violations else "fixed", "quality_gate_failed": bool(violations),
            "needs_rewrite": bool(violations), "retry_count": retry_count, "retry_modes": modes, "failure_reasons": violations,
            "_llm_calls": llm_calls_meta}
