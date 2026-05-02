from __future__ import annotations
import json, re
from .llm_runtime import call as llm_call

_PROMPT = (
    "你是情感提炼师。根据歌词意图和风格画像，提炼关系状态与演唱动机。\n"
    "意图：{intent}\n风格画像：{portrait}\n"
    "只输出中文，不允许英文词；歌手名或英文歌名可保留。\n"
    "inner_motive：中文一句，<=15字，必须是关系状态/内在动机，不得写视觉场景。\n"
    "arc：中文情绪曲线，如'压抑→冲动→克制→释然'。\n"
    "hook_seed：中文一句，<=12字，口语化，且含矛盾感或反问。\n"
    "输出严格 JSON（无 markdown，无注释）：\n"
    '{{"inner_motive":"...","arc":"...","hook_seed":"..."}}'
)

def distill_emotion(intent: str, portrait: dict[str, object]) -> dict[str, str]:
    prompt = _PROMPT.format(intent=intent or "", portrait=json.dumps(portrait, ensure_ascii=False))
    content, llm_meta = llm_call(prompt, temperature=0.3)
    s = re.sub(r'^```(?:json)?\s*', '', content.strip())
    s = re.sub(r'\s*```$', '', s)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        i, j = s.find('{'), s.rfind('}')
        if i == -1 or j == -1:
            raise RuntimeError(f"distill_emotion: non-JSON from LLM: {s[:200]}")
        data = json.loads(s[i:j + 1])
    data.setdefault("inner_motive", "想联络却不敢")
    data.setdefault("arc", "压抑→冲动→克制→释然")
    data.setdefault("hook_seed", "我还要等你吗")
    data["_llm_meta"] = [llm_meta]
    return data
