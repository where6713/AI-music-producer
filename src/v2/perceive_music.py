from __future__ import annotations
import json, re
from pathlib import Path
from .llm_runtime import call as llm_call

KNOWN = {
    "HYBS": {"genre_guess": "indie pop", "bpm_range": "100-120", "vibe": "公路慵懒"},
    "deca joins": {"genre_guess": "indie", "bpm_range": "80-100", "vibe": "午后漂移"},
    "周杰伦": {"genre_guess": "流行", "bpm_range": "80-100", "vibe": "青春叙事"},
    "五月天": {"genre_guess": "摇滚", "bpm_range": "120-140", "vibe": "热血群唱"},
    "张悬": {"genre_guess": "folk", "bpm_range": "80-100", "vibe": "私语亲密"},
    "Khalil Fong": {"genre_guess": "R&B", "bpm_range": "80-100", "vibe": "律动松弛"},
    "蔡依林": {"genre_guess": "流行", "bpm_range": "100-120", "vibe": "议题张力"},
    "林俊杰": {"genre_guess": "流行", "bpm_range": "80-100", "vibe": "情绪推进"},
}

_PROMPT = (
    "你是音乐风格分析师。根据意图和参考，推断风格画像。\n"
    "意图：{intent}\n参考音乐/艺人：{ref}\n已知风格提示：{hint}\n"
    "genre_guess 候选值：indie pop / 流行 / classical_cn / R&B / folk / 摇滚 / EDM\n"
    "输出严格 JSON（无 markdown 包裹，无注释）：\n"
    '{{"genre_guess":"...","bpm_range":"...","vibe":"...","intent":"..."}}'
)

def perceive_music(intent: str, ref_audio: str = "") -> dict[str, object]:
    hint = ""
    for key, meta in KNOWN.items():
        if key.lower() in (intent or "").lower() or key.lower() in str(ref_audio).lower():
            hint = json.dumps(meta, ensure_ascii=False)
            break
    audio_hint = Path(ref_audio).suffix.lower() if ref_audio else "none"
    prompt = _PROMPT.format(intent=intent or "", ref=ref_audio or "无", hint=hint or "无")
    content, llm_meta = llm_call(prompt, temperature=0.3)
    s = re.sub(r'^```(?:json)?\s*', '', content.strip())
    s = re.sub(r'\s*```$', '', s)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        i, j = s.find('{'), s.rfind('}')
        if i == -1 or j == -1:
            raise RuntimeError(f"perceive_music: non-JSON from LLM: {s[:200]}")
        data = json.loads(s[i:j + 1])
    data.setdefault("genre_guess", "indie pop")
    data.setdefault("bpm_range", "80-100")
    data.setdefault("vibe", "夜色情绪")
    data.setdefault("intent", intent or "")
    data["audio_hint"] = audio_hint
    data["_llm_meta"] = [llm_meta]
    return data
