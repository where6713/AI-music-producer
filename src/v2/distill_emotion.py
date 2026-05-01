from __future__ import annotations


def distill_emotion(intent: str, portrait: dict[str, object]) -> dict[str, str]:
    text = (intent or "").strip()
    low = text.lower()
    valence = "mixed"
    if any(k in low for k in ("失恋", "难过", "痛", "孤独", "离开")):
        valence = "negative"
    elif any(k in low for k in ("开心", "希望", "阳光", "热恋")):
        valence = "positive"
    arc = "hold-and-release"
    if valence == "negative":
        arc = "descend-then-breathe"
    if valence == "positive":
        arc = "lift-and-resolve"
    central_image = "灯火"
    if "classical" in str(portrait.get("genre_guess", "")):
        central_image = "青瓷与旧雨"
    elif "indie" in str(portrait.get("genre_guess", "")):
        central_image = "末班公交车"
    metaphor = "weather as feeling"
    return {
        "valence": valence,
        "arc": arc,
        "central_image": central_image,
        "metaphor": metaphor,
        "intent_focus": text[:120],
    }
