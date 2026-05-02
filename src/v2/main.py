from __future__ import annotations

from pathlib import Path
import json

from ._io import dump_outputs, parse_cli
from .compose import compose
from .distill_emotion import distill_emotion
from .llm_runtime import call as llm_call
from .perceive_music import perceive_music
from .select_corpus import select_corpus
from .self_review import self_review


def _load_selected_context(ids: list[str]) -> tuple[str, int]:
    parts: list[str] = []
    for sid in ids:
        p = Path(sid)
        if p.exists() and p.is_file():
            try:
                parts.append(p.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                parts.append(p.read_text(encoding="utf-8-sig"))
    text = "\n".join(parts)
    return text, len(text)


def run_v2(raw_intent: str, ref_audio: str = "", index_path: str = "corpus/_index.json") -> dict[str, object]:
    llm_calls: list[dict[str, object]] = []
    _c1, t1 = llm_call(f"perceive music\nintent={raw_intent}\nref_audio={ref_audio}", temperature=0.5)
    t1["step"] = "perceive_music"
    llm_calls.append(t1)
    portrait = perceive_music(raw_intent, ref_audio=ref_audio)

    _c2, t2 = llm_call(f"distill emotion\nintent={raw_intent}\nportrait={json.dumps(portrait, ensure_ascii=False)}", temperature=0.5)
    t2["step"] = "distill_emotion"
    llm_calls.append(t2)
    emotion = distill_emotion(raw_intent, portrait)
    pool = select_corpus(Path(index_path), portrait, limit=100)
    preferred = [x for x in pool if "slot01_indie_lazy" in str(x.get("id", ""))]
    golden = (preferred + [x for x in pool if "golden_dozen" in str(x.get("id", ""))])[:12]

    _c3, t3 = llm_call(
        f"compose pass1 select ids\nintent={raw_intent}\nportrait={json.dumps(portrait, ensure_ascii=False)}\npool={json.dumps([x.get('id','') for x in pool[:120]], ensure_ascii=False)}",
        temperature=0.7,
    )
    t3["step"] = "compose_pass1"
    llm_calls.append(t3)

    selected_ids = [str(x.get("id", "")) for x in golden]
    ctx_text, pass2_context_chars = _load_selected_context(selected_ids)
    if pass2_context_chars < 200:
        slot01 = [x for x in pool if "slot01_indie_lazy" in str(x.get("id", ""))]
        fallback_ids = [str(x.get("id", "")) for x in slot01[:1]]
        ctx_text, pass2_context_chars = _load_selected_context(fallback_ids)
    _c4, t4 = llm_call(
        f"compose pass2 with full context\nintent={raw_intent}\ncontext={ctx_text}",
        temperature=0.7,
    )
    t4["step"] = "compose_pass2"
    llm_calls.append(t4)

    draft = compose(portrait, emotion, golden_refs=golden, corpus_pool=pool)
    _c5, t5 = llm_call(f"self review\nlyrics={draft.get('lyrics','')}", temperature=0.5)
    t5["step"] = "self_review"
    llm_calls.append(t5)
    final = self_review(draft)
    final["portrait"] = portrait
    final["emotion"] = emotion
    final["recalled_pool_size"] = len(pool)
    final["golden_refs_used"] = len(golden)
    final["pass2_context_chars"] = pass2_context_chars
    final["llm_calls"] = llm_calls
    return final


if __name__ == "__main__":
    args = parse_cli()
    out = run_v2(args.intent, ref_audio=args.ref_audio, index_path=args.index)
    out_dir = Path(args.out)
    dump_outputs(out_dir, out)
    print(f"done: {out_dir}")
