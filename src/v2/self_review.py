from __future__ import annotations
from ._review_prompts import PROMPT
from .llm_runtime import call as llm_call

def self_review(draft: dict[str, object], max_retries: int = 1) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    brief = draft.get("brief") if isinstance(draft.get("brief"), dict) else {}
    revised, meta = llm_call(PROMPT.format(brief=brief, lyrics=lyrics), temperature=0.3)
    return {**dict(draft), "lyrics": revised.strip() or lyrics, "review_skipped": False, "_llm_calls": [meta]}
