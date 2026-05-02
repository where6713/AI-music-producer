from __future__ import annotations
import json
from .llm_runtime import call as llm_call

PROMPT = (
    "你是华语顶级作词人。基于输入写200-400字创作笔记。"
    "自然涵盖:一个可承载思念的具体物件、一句可当歌名的<=8字陈述句、"
    "三段情绪推进、一个十三辙韵部及理由。"
    "采用连续散文段落表达创作札记。\n意图:{intent}\n画像:{portrait}"
)


def distill_emotion(intent: str, portrait: dict[str, object]) -> dict[str, object]:
    text, meta = llm_call(PROMPT.format(intent=intent or "", portrait=json.dumps(portrait, ensure_ascii=False)), temperature=0.3)
    brief = text.strip() or "用票根写一首夜路情歌 标题句是我先睡了 情绪从否认到承认再放过 韵部用江阳"
    return {"brief": brief, "_llm_meta": [meta]}
