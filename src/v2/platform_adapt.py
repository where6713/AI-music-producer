from __future__ import annotations
import json
from .llm_runtime import call as llm_call
from ._platform_prompts import ADAPT


class PlatformAdaptError(RuntimeError):
    pass


def adapt(lyrics: str, portrait: dict[str, object]) -> tuple[dict[str, str], dict[str, object]]:
    raw, meta = llm_call(ADAPT.format(lyrics=lyrics, portrait=json.dumps(portrait, ensure_ascii=False)), temperature=0.3)
    try:
        obj = json.loads(raw.strip())
        return {"style": str(obj.get("style", "")), "exclude": str(obj.get("exclude", ""))}, {"platform_adapt_status": "ok", "platform_adapt_raw_response": raw, **meta}
    except Exception as e:
        raise PlatformAdaptError(raw) from e
