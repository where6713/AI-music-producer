from __future__ import annotations
from pathlib import Path
from ._io import dump_outputs, parse_cli
from .compose import compose
from .distill_emotion import distill_emotion
from .perceive_music import perceive_music
from .select_corpus import extract_anchor_chorus, select_corpus, select_golden_anchors_with_mode
from .second_pass import second_pass
from ._persona import select_persona_a, PERSONA_BANK, PERSONA_B
from .platform_adapt import PlatformAdaptError, adapt
import os, sys

def run_v2(raw_intent: str, ref_audio: str = "", index_path: str = "corpus/_index.json") -> dict[str, object]:
    portrait = perceive_music(raw_intent, ref_audio=ref_audio)
    portrait["persona_used"] = select_persona_a(portrait)
    brief = distill_emotion(raw_intent, portrait)
    pool = select_corpus(Path(index_path), portrait, limit=100)
    golden, selection_mode = select_golden_anchors_with_mode(pool, portrait)
    portrait["selection_mode"] = selection_mode
    anchor_path = str(golden[0].get("id", "")) if golden else ""
    anchor_song_name = Path(anchor_path).name if anchor_path else ""
    anchor_chorus = extract_anchor_chorus(anchor_path) if anchor_path else ""
    anchor_chorus_status = "explicit_tag"
    if anchor_chorus and ("[" not in anchor_chorus and "【" not in anchor_chorus):
        anchor_chorus_status = "repeated_block" if "\n" in anchor_chorus else "dense_middle"
    if not anchor_chorus.strip():
        anchor_chorus_status = "approximated_raw"
    draft = compose(portrait, brief, golden_refs=golden, corpus_pool=pool)
    a_lyrics = str(draft.get("lyrics", ""))
    final = second_pass(draft)
    b_lyrics = str(final.get("lyrics", ""))
    review_decision = str(final.get("review_decision", "revised"))
    review_reason = str(final.get("review_reason", ""))
    platform_status, platform_raw = "ok", ""
    try:
        pack, meta_adapt = adapt(b_lyrics, portrait)
        final.update(style=pack.get("style", ""), exclude=pack.get("exclude", ""))
        platform_raw = str(meta_adapt.get("platform_adapt_raw_response", ""))
    except PlatformAdaptError as e:
        platform_status, platform_raw = "json_parse_failed", str(e)
        final.setdefault("style", "")
        final.setdefault("exclude", "")
        if not os.getenv("V2_SMOKE_VERBOSE") == "1":
            raise
    all_m = portrait.get("_llm_meta", []) + brief.get("_llm_meta", []) + draft.get("_llm_calls", []) + final.get("_llm_calls", [])
    final.update(
        portrait=portrait,
        emotion_focus=brief.get("emotion_focus", ""),
        persona_used=portrait.get("persona_used", ""),
        selected_ids=[Path(str(x.get("id", ""))).name for x in golden if str(x.get("id", ""))],
        anchor_source_paths=[str(x.get("id", "")) for x in golden if str(x.get("id", ""))],
        anchor_song_name=anchor_song_name,
        anchor_chorus_status=anchor_chorus_status,
        anchor_chorus=anchor_chorus,
        review_decision=review_decision,
        review_reason=review_reason,
        lyrics_changed=(a_lyrics.strip() != b_lyrics.strip()),
        platform_adapt_status=platform_status,
        platform_adapt_raw_response=platform_raw,
        review_skipped=False,
        llm_total_calls=len(all_m),
        llm_total_input_tokens=sum(int(m.get("tokens_in", 0)) for m in all_m),
        llm_total_output_tokens=sum(int(m.get("tokens_out", 0)) for m in all_m),
    )
    if os.getenv("V2_SMOKE_VERBOSE") == "1":
        out_dir = Path(os.getenv("V2_SMOKE_OUT", "out/runs/patch7_smoke_1"))
        out_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            f"[DISTILL] emotion_focus: {brief.get('emotion_focus','')}",
            f"[ANCHOR] song_name: {anchor_song_name} / chorus excerpt:\n{anchor_chorus}",
            f"[PERSONA_A] selected: {portrait.get('persona_used','')}",
            "[AGENT_A LYRICS START]\n" + a_lyrics + "\n[AGENT_A LYRICS END]",
            f"[AGENT_B DECISION]: {review_decision}",
            "[AGENT_B LYRICS START]\n" + b_lyrics + "\n[AGENT_B LYRICS END]",
            f"[AGENT_C STATUS]: {platform_status}",
            f"[FINAL]: lyrics={bool(final.get('lyrics'))} style={bool(final.get('style'))} exclude={bool(final.get('exclude'))}",
        ]
        (out_dir / "debug_verbose.txt").write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print("SMOKE_VERBOSE_WRITTEN")
    return final

if __name__ == "__main__":
    args = parse_cli()
    out = run_v2(args.intent, ref_audio=args.ref_audio, index_path=args.index)
    dump_outputs(Path(args.out), out)
    print(f"done: {Path(args.out)}")
