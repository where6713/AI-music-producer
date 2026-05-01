from __future__ import annotations

from pathlib import Path


def perceive_music(intent: str, ref_audio: str = "") -> dict[str, object]:
    text = (intent or "").strip()
    low = text.lower()
    tempo = "mid"
    if any(k in low for k in ("dance", "edm", "快", "躁", "燃")):
        tempo = "fast"
    elif any(k in low for k in ("慢", "夜", "静", "疗愈", "雨")):
        tempo = "slow"
    energy = "medium"
    if tempo == "fast":
        energy = "high"
    if tempo == "slow":
        energy = "low"
    texture = "urban introspective"
    if any(k in low for k in ("古风", "国风", "古典")):
        texture = "classical chinese"
    elif any(k in low for k in ("indie", "慵懒", "松弛", "bedroom")):
        texture = "indie lazy groove"
    elif any(k in low for k in ("流行", "青春", "阳光")):
        texture = "pop bright"
    audio_hint = "none"
    if ref_audio:
        audio_hint = Path(ref_audio).suffix.lower() or "path"
    return {
        "tempo": tempo,
        "energy": energy,
        "texture": texture,
        "audio_hint": audio_hint,
        "intent": text,
    }
