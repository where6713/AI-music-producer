from __future__ import annotations
import json, re
from pathlib import Path
from .llm_runtime import call as llm_call

_P1 = (
    "从以下语料 ID 列表中选 3-8 个与风格/情感最相关的 ID。\n"
    "风格：{portrait}\n情感：{emotion}\n黄金参考（内容摘要）：{golden}\n"
    "语料 IDs（最多120条）：{pool}\n"
    '输出 JSON array（仅含原 ID 字符串，无其他文字）：["id1","id2",...]'
)
_P2 = (
    "你是歌词创作大师。创作完整中文歌词，≥12行，含[Verse]+[Chorus]段落。\n"
    "风格：{portrait}\n情感：{emotion}\n"
    "黄金参考（{n}首，学习意象和句式）：\n{golden}\n参考片段：\n{selected}\n"
    "硬性禁止：我把 / 让X成为 / 中英混搭 / 孤立主语+动宾结构\n"
    "押韵自然，意象具体，不用陈词滥调（站台/晚安/星空等）。\n"
    '输出 JSON：{{"lyrics":"...","style":"...","exclude":"..."}}'
)

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
    pool_ids = json.dumps([str(x.get("id", "")) for x in corpus_pool[:120]], ensure_ascii=False)
    c1, m1 = llm_call(_P1.format(portrait=ps, emotion=es, golden=golden_texts, pool=pool_ids), temperature=0.5)
    try:
        raw_ids = json.loads(c1)
    except Exception:
        raw_ids = []
    pool_id_set = {str(x.get("id", "")) for x in corpus_pool}
    ids = [i for i in (raw_ids if isinstance(raw_ids, list) else []) if i in pool_id_set]
    selected_texts = _load_texts(ids)
    c2, m2 = llm_call(_P2.format(portrait=ps, emotion=es, golden=golden_texts, selected=selected_texts, n=len(golden_refs)), temperature=0.9)
    s = re.sub(r'^```(?:json)?\s*', '', c2.strip())
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
    result["_llm_calls"] = [m1, m2]
    return result
