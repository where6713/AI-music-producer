from __future__ import annotations

from pathlib import Path

from .compose import compose
from .distill_emotion import distill_emotion
from .perceive_music import perceive_music
from .select_corpus import select_corpus
from .self_review import self_review


def run_v2(raw_intent: str, ref_audio: str = "", index_path: str = "corpus/_index.json") -> dict[str, object]:
    portrait = perceive_music(raw_intent, ref_audio=ref_audio)
    emotion = distill_emotion(raw_intent, portrait)
    pool = select_corpus(Path(index_path), portrait, limit=100)
    golden = [x for x in pool if "golden_dozen" in str(x.get("id", ""))][:12]
    draft = compose(portrait, emotion, golden_refs=golden, corpus_pool=pool)
    final = self_review(draft)
    final["portrait"] = portrait
    final["emotion"] = emotion
    final["recalled_pool_size"] = len(pool)
    final["golden_refs_used"] = len(golden)
    return final


if __name__ == "__main__":
    import argparse
    import json as _json
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", default="")
    parser.add_argument("--ref-audio", default="")
    parser.add_argument("--index", default="corpus/_index.json")
    parser.add_argument("--out", default="out/runs/smoke")
    args = parser.parse_args()
    out = run_v2(args.intent, ref_audio=args.ref_audio, index_path=args.index)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lyrics.txt").write_text(str(out.get("lyrics", "")), encoding="utf-8")
    (out_dir / "style.txt").write_text(str(out.get("style", "")), encoding="utf-8")
    (out_dir / "exclude.txt").write_text(str(out.get("exclude", "")), encoding="utf-8")
    trace = {
        "portrait": out.get("portrait") if isinstance(out.get("portrait"), dict) else {},
        "emotion": out.get("emotion") if isinstance(out.get("emotion"), dict) else {},
        "selected_ids": out.get("selected_ids", []),
        "review_notes": out.get("review_note", ""),
    }
    (out_dir / "trace.json").write_text(_json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {out_dir}")
