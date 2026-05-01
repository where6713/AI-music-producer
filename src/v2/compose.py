from __future__ import annotations


def compose(
    portrait: dict[str, object],
    emotion: dict[str, str],
    golden_refs: list[dict[str, object]],
    corpus_pool: list[dict[str, object]],
) -> dict[str, object]:
    pick_ids = [str(x.get("id", "")) for x in corpus_pool[:8] if isinstance(x, dict)]
    vibe = str(portrait.get("texture", ""))
    image = emotion.get("central_image", "city lights")
    hook = "我把晚安留给未来"
    if "indie" in vibe:
        hook = "风把想念吹成了节拍"
    if "classical" in vibe:
        hook = "一盏青灯照见旧人间"
    lyrics = "\n".join(
        [
            "[Verse]",
            f"{image}在窗边慢慢褪色",
            "我把沉默折进外套口袋",
            "路灯像没说完的话",
            "脚步在夜里轻轻来回",
            "",
            "[Chorus]",
            hook,
            "等风停在你不在的站台",
            "我学着把心事放开",
            "让天亮替我回答",
        ]
    )
    return {
        "selected_ids": pick_ids,
        "golden_refs_used": len(golden_refs),
        "lyrics": lyrics,
        "style": f"{vibe}; {emotion.get('arc','hold-and-release')}",
        "exclude": "overwritten metaphor, cliché slogans",
    }
