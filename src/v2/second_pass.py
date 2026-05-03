from __future__ import annotations
from ._prompts import POLISH_PROMPT, PERSONA_B
from .llm_runtime import call as llm_call


def _changed_lines(a: str, b: str) -> list[int]:
    x, y = a.splitlines(), b.splitlines()
    n = max(len(x), len(y))
    return [i + 1 for i in range(n) if (x[i] if i < len(x) else "") != (y[i] if i < len(y) else "")]


def second_pass(draft: dict[str, object]) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    brief = str(draft.get("brief", {}).get("emotion_focus", "") if isinstance(draft.get("brief"), dict) else "")
    out, meta = llm_call(POLISH_PROMPT.format(persona_b=PERSONA_B, emotion_focus=brief, lyrics=lyrics), temperature=0.3)
    txt = (out or "").strip() or lyrics
    decision, reason = ("kept_as_is", txt.splitlines()[0][1:].strip()) if txt.startswith("#") else ("revised", "")
    if txt.startswith("#"):
        txt = "\n".join(txt.splitlines()[1:]).strip()
    return {**dict(draft), "lyrics": txt, "review_decision": decision, "review_reason": reason, "lyrics_changed": txt != lyrics, "polish_passes": 1, "polish_diffs": _changed_lines(lyrics, txt), "_llm_calls": [meta]}
