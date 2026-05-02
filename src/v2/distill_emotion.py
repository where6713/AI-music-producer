from __future__ import annotations
import json
from .llm_runtime import call as llm_call
from ._persona import PERSONA_BANK

PROMPT = (
    "{persona}\n"
    "下面是一首歌的背景:\n{portrait}\n{intent}\n"
    "在动笔写之前 先用一句话告诉自己这首歌讲什么。"
    "格式: <谁> 在 <场景> 对 <谁或什么> 做了 <什么>。"
    "直接输出这一句话。"
)


def distill_emotion(intent: str, portrait: dict[str, object]) -> dict[str, object]:
    persona = PERSONA_BANK.get(str(portrait.get("persona_used", "li_zongsheng")), PERSONA_BANK["li_zongsheng"])
    text, meta = llm_call(PROMPT.format(intent=intent or "", portrait=json.dumps(portrait, ensure_ascii=False), persona=persona), temperature=0.3)
    focus = text.strip() or "她在凌晨的路上 对没放下的人 说了再见"
    return {"emotion_focus": focus[:40], "_llm_meta": [meta]}
