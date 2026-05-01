from __future__ import annotations

from pathlib import Path


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


def perceive_music(intent: str, ref_audio: str = "") -> dict[str, object]:
    text = (intent or "").strip()
    low = text.lower()
    for key, meta in KNOWN.items():
        if key.lower() in low or (ref_audio and key.lower() in str(ref_audio).lower()):
            out = dict(meta)
            out["intent"] = text
            out["audio_hint"] = Path(ref_audio).suffix.lower() if ref_audio else "none"
            return out
    tempo = "mid"
    if any(k in low for k in ("dance", "edm", "快", "躁", "燃")):
        tempo = "fast"
    elif any(k in low for k in ("慢", "夜", "静", "疗愈", "雨")):
        tempo = "slow"
    energy = {"fast": "high", "slow": "low"}.get(tempo, "medium")
    genre = "indie pop"
    if any(k in low for k in ("古风", "国风", "古典")):
        genre = "classical_cn"
    elif any(k in low for k in ("indie", "慵懒", "松弛", "bedroom")):
        genre = "indie pop"
    elif any(k in low for k in ("流行", "青春", "阳光")):
        genre = "流行"
    bpm = {"fast": "120-140", "slow": "<80"}.get(tempo, "80-100")
    vibe = "雨夜独白"
    if tempo == "fast":
        vibe = "派对前夜"
    return {
        "genre_guess": genre,
        "bpm_range": bpm,
        "vibe": vibe,
        "audio_hint": Path(ref_audio).suffix.lower() if ref_audio else "none",
        "intent": text,
    }
