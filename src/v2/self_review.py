from __future__ import annotations


def self_review(draft: dict[str, object]) -> dict[str, object]:
    lyrics = str(draft.get("lyrics", "")).strip()
    lines = [ln.rstrip() for ln in lyrics.splitlines()]
    polished = []
    for ln in lines:
        if ln and not ln.startswith("["):
            polished.append(ln.replace("慢慢", "缓缓"))
        else:
            polished.append(ln)
    out = dict(draft)
    out["lyrics"] = "\n".join(polished)
    out["review_note"] = "light expression polish; structure unchanged"
    return out
