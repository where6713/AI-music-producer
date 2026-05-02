from __future__ import annotations
import json, re
from .llm_runtime import call as llm_call

_PROMPT = (
    "你是情感提炼师。根据歌词意图和风格画像，提炼情感参数。\n"
    "意图：{intent}\n风格画像：{portrait}\n"
    "valence 判断规则（必须严格遵守）：\n"
    "  含'失恋/难过/痛/孤独/离开/分手/一个人' → negative\n"
    "  含'开心/希望/阳光/热恋/喜欢/快乐' → positive\n"
    "  其他 → mixed\n"
    "arc 规则：negative→descend-then-breathe; positive→lift-and-resolve; mixed→hold-and-release\n"
    "输出严格 JSON（无 markdown，无注释）：\n"
    '{{"valence":"...","arc":"...","central_image":"(中文意象,≤10字)","metaphor":"...","intent_focus":"..."}}'
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
    data.setdefault("valence", "mixed")
    data.setdefault("arc", "hold-and-release")
    data.setdefault("central_image", "灯火")
    data.setdefault("metaphor", "weather as feeling")
    data.setdefault("intent_focus", (intent or "")[:120])
    data["_llm_meta"] = [llm_meta]
    return data
