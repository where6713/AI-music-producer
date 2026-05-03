from __future__ import annotations
import json, re
from .llm_runtime import call as llm_call
from ._prompts import DISTILL_PROMPT, PERSONA_BANK

def distill_emotion(intent: str, portrait: dict[str, object]) -> dict[str, object]:
    persona = PERSONA_BANK.get(str(portrait.get("persona_used", "li_zongsheng")), PERSONA_BANK["li_zongsheng"])
    p = DISTILL_PROMPT.format(intent=intent or "", portrait=json.dumps(portrait, ensure_ascii=False), persona=persona)
    bad = re.compile(r"[<>]|\b[XYZ]\b|我 在|对 你|做了")
    out, meta = "", {}
    for _ in range(2):
        out, meta = llm_call(p, temperature=0.3)
        s = (out or "").strip()
        if 15 <= len(s) <= 40 and not bad.search(s):
            return {"emotion_focus": s, "_llm_meta": [meta]}
    raise RuntimeError(f"distill_emotion: invalid emotion_focus: {out[:120]}")
