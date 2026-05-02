from __future__ import annotations
import json, re
from pathlib import Path
from .llm_runtime import call as llm_call

_P1 = (
    "你是中文流行歌词作者。请写完整歌词，>=12行，包含[Verse]和[Chorus]。\n"
    "风格：{portrait}\n情感：{emotion}\n黄金参考（{n}首，仅学习口语节奏与关系状态）：\n{golden}\n"
    "黑名单意象：霓虹/便利店/高架/咖啡店/咖啡/雨刷/仪表盘/收费站/护栏/副驾/安全带/导航。\n"
    "黑名单句式：将...叠折收、替...做...、学会...(平常/不追问/别说)、塞进...里、心跳挤满...、...肯收留...。\n"
    "正向要求：副歌必须有hook(<=10字、口语、可重复、含矛盾或反问)；鼓励反反覆覆/起起伏伏/来来回回；\n"
    "可少量用语气词(吧/啊/呢/呀)；优先写关系状态(戒不掉/删了又写/按不下发送键)不写场景配件；副歌至少1句重复>=2次。\n"
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
    ids = [str(x.get("id", "")) for x in golden_refs[:2] if str(x.get("id", ""))]
    pre = ""
    if str(portrait.get("selection_mode", "")) == "empty_pool":
        pre = "⚠️ 当前无 anchor 参考,请严格按 motive/hook_seed 创作,不得堆砌套话\n"
    c1, m1 = llm_call(pre + _P1.format(portrait=ps, emotion=es, golden=golden_texts, n=len(golden_refs)), temperature=0.9)
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
