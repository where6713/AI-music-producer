from __future__ import annotations
from ._quality_rules import check
from .llm_runtime import call as llm_call

_PROMPT = (
    "修改以下歌词，消除所有违规项并通过主观检查，保持原有段落结构（不增删[Section]标记）。\n"
    "原歌词：\n{lyrics}\n违规项：{violations}\n"
    "主观检查：Q1副歌是否有hook(<=10字/口语/可重复/含矛盾或反问)，没有就改写副歌；\n"
    "Q2 verse若堆砌视觉场景道具，退一步改为情绪状态本身；\n"
    "Q3 若有倒装或欧化句(替...做.../将...折好)，改成口语直叙。\n"
    "仅输出修改后的完整歌词文本（无 JSON，无任何额外说明）。"
)

def self_review(draft: dict[str, object], max_retries: int = 1) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    violations = check(lyrics)
    out = dict(draft)
    retry_count = 0
    llm_calls_meta: list[dict[str, object]] = []
    if not violations:
        return {**out, "review_notes": "passed", "quality_gate_failed": False, "retry_count": 0, "_llm_calls": []}
    for _ in range(max_retries):
        retry_count += 1
        prompt = _PROMPT.format(lyrics=lyrics, violations="; ".join(violations))
        content, meta = llm_call(prompt, temperature=0.3)
        llm_calls_meta.append(meta)
        lyrics = content.strip()
        violations = check(lyrics)
        if not violations:
            break
    note = "; ".join(violations) if violations else "fixed"
    return {**out, "lyrics": lyrics, "review_notes": note, "quality_gate_failed": bool(violations),
            "needs_rewrite": bool(violations), "retry_count": retry_count, "_llm_calls": llm_calls_meta}
