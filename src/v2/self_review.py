from __future__ import annotations
from ._quality_rules import check
from ._review_prompts import SURGICAL
from .llm_runtime import call as llm_call

def _brief_violations(text: str, brief: dict[str, object]) -> list[str]:
    hook = str(brief.get("cognitive_hook", "")).strip()
    v = []
    lines = [x.strip() for x in text.splitlines()]
    c0 = next((i for i, x in enumerate(lines) if x == "[Chorus]"), -1)
    c_lines = []
    if c0 >= 0:
        for s in lines[c0 + 1:]:
            if s.startswith("["):
                break
            if s:
                c_lines.append(s)
    hook_ok = bool(c_lines) and (c_lines[0] == hook or c_lines[-1] == hook)
    if not hook or "?" in hook or "？" in hook or len(hook) > 8 or hook.endswith(("吗", "呢", "吧")) or not hook_ok:
        v.append("brief_violation_hook")
    secs = [s for s in text.splitlines() if s.startswith("[")]
    if len(secs) < 4 or any(s.startswith("[Verse 3]") for s in secs):
        v.append("brief_violation_structure")
    return v


def _physics_lines(text: str) -> list[str]:
    bad = []
    for line in [x.strip() for x in text.splitlines() if x.strip() and not x.strip().startswith("[")]:
        if any(k in line for k in ("夜色吹", "后视镜看座椅", "直线拉昨夜", "不争对", "昨夕", "空单", "借题", "云纹")):
            bad.append(line)
    return bad


def self_review(draft: dict[str, object], max_retries: int = 1) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    hard, _ = check(lyrics)
    brief = draft.get("brief") if isinstance(draft.get("brief"), dict) else {}
    physics0 = _physics_lines(lyrics)
    violations = hard + _brief_violations(lyrics, brief) + (["physics_violation"] if physics0 else [])
    out = dict(draft)
    if not violations:
        return {**out, "review_notes": {"physics_violations": []}, "quality_gate_failed": False, "retry_count": 0, "retry_modes": [], "failure_reasons": [], "_llm_calls": []}
    retry_count, llm_calls_meta, modes = 1, [], ["surgical_fix"]
    content, meta = llm_call(SURGICAL.format(brief=brief, lyrics=lyrics), temperature=0.3)
    llm_calls_meta.append(meta)
    lyrics = content.strip()
    hard, _ = check(lyrics)
    physics1 = _physics_lines(lyrics)
    violations = hard + _brief_violations(lyrics, brief) + (["physics_violation"] if physics1 else [])
    notes = [f"{a} => {b}" for a, b in zip(physics0, physics1)] if physics0 and physics1 else []
    return {**out, "lyrics": lyrics, "review_notes": {"physics_violations": notes}, "quality_gate_failed": bool(violations),
            "needs_rewrite": bool(violations), "retry_count": retry_count, "retry_modes": modes, "failure_reasons": violations,
            "_llm_calls": llm_calls_meta}
