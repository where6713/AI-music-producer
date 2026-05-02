from __future__ import annotations
from pathlib import Path
from ._io import dump_outputs, parse_cli
from .compose import compose
from .distill_emotion import distill_emotion
from .perceive_music import perceive_music
from .select_corpus import select_corpus, select_golden_anchors_with_mode
from .self_review import self_review

def run_v2(raw_intent: str, ref_audio: str = "", index_path: str = "corpus/_index.json") -> dict[str, object]:
    portrait = perceive_music(raw_intent, ref_audio=ref_audio)
    emotion = distill_emotion(raw_intent, portrait)
    pool = select_corpus(Path(index_path), portrait, limit=100)
    golden, selection_mode = select_golden_anchors_with_mode(pool, portrait)
    draft = compose(portrait, emotion, golden_refs=golden, corpus_pool=pool)
    final = self_review(draft)
    all_m = portrait.get("_llm_meta", []) + emotion.get("_llm_meta", []) + draft.get("_llm_calls", []) + final.get("_llm_calls", [])
    final.update(portrait=portrait, motive=emotion.get("inner_motive", ""), hook_seed=emotion.get("hook_seed", ""),
                 selection_mode=selection_mode, recalled_pool_size=len(pool),
                  golden_refs_used=draft.get("golden_refs_used", 0), llm_total_calls=len(all_m),
                  llm_total_input_tokens=sum(int(m.get("tokens_in", 0)) for m in all_m),
                  llm_total_output_tokens=sum(int(m.get("tokens_out", 0)) for m in all_m))
    final.pop("emotion", None)
    return final

if __name__ == "__main__":
    args = parse_cli()
    out = run_v2(args.intent, ref_audio=args.ref_audio, index_path=args.index)
    dump_outputs(Path(args.out), out)
    print(f"done: {Path(args.out)}")
