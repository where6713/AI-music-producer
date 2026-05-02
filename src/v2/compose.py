from __future__ import annotations
import json, re
from pathlib import Path
from ._compose_prompts import P1
from .llm_runtime import call as llm_call

def _load_texts(ids: list[str]) -> str:
    parts = []
    for sid in ids:
        p = Path(sid)
        if p.exists():
            try:
                parts.append(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return "\n---\n".join(parts) if parts else "(无参考文本)"

def compose(portrait, emotion, golden_refs, corpus_pool) -> dict[str, object]:
    ps = json.dumps(portrait, ensure_ascii=False)
    es = json.dumps(emotion, ensure_ascii=False)
    golden_texts = _load_texts([str(x.get("id", "")) for x in golden_refs])
    ids = [str(x.get("id", "")) for x in golden_refs[:2] if str(x.get("id", ""))]
    pre = ""
    if str(portrait.get("selection_mode", "")) == "empty_pool":
        pre = "⚠️ 当前无 anchor 参考,请严格按 motive/hook_seed 创作,不得堆砌套话\n"
    c1, m1 = llm_call(pre + P1.format(portrait=ps, emotion=es, golden=golden_texts, n=len(golden_refs)), temperature=0.9)
    s = re.sub(r'^```(?:json)?\s*', '', c1.strip())
    s = re.sub(r'\s*```$', '', s)
    try:
        result = json.loads(s)
    except Exception:
        i, j = s.find('{'), s.rfind('}')
        if i == -1 or j == -1:
            raise RuntimeError(f"compose pass2: non-JSON from LLM: {s[:200]}")
        result = json.loads(s[i:j + 1])
    result["selected_ids"] = ids
    result["golden_refs_used"] = len(golden_refs)
    result["pass1_selected_ids_count"] = len(ids)
    result["_llm_calls"] = [m1]
    return result
