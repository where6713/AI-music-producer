from __future__ import annotations

from pathlib import Path

from ._io import dump_outputs, parse_cli
from .compose import compose
from .distill_emotion import distill_emotion
from .perceive_music import perceive_music
from .select_corpus import select_corpus
from .self_review import self_review


def run_v2(raw_intent: str, ref_audio: str = "", index_path: str = "corpus/_index.json") -> dict[str, object]:
    portrait = perceive_music(raw_intent, ref_audio=ref_audio)
    emotion = distill_emotion(raw_intent, portrait)
    pool = select_corpus(Path(index_path), portrait, limit=100)
    preferred = [x for x in pool if "slot01_indie_lazy" in str(x.get("id", ""))]
    golden = (preferred + [x for x in pool if "golden_dozen" in str(x.get("id", ""))])[:12]
    draft = compose(portrait, emotion, golden_refs=golden, corpus_pool=pool)
    final = self_review(draft)
    final["portrait"] = portrait
    final["emotion"] = emotion
    final["recalled_pool_size"] = len(pool)
    final["golden_refs_used"] = len(golden)
    return final


if __name__ == "__main__":
    args = parse_cli()
    out = run_v2(args.intent, ref_audio=args.ref_audio, index_path=args.index)
    out_dir = Path(args.out)
    dump_outputs(out_dir, out)
    print(f"done: {out_dir}")
