from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    for flag, default in [("--intent", ""), ("--ref-audio", ""), ("--index", "corpus/_index.json"), ("--out", "out/runs/smoke")]:
        p.add_argument(flag, default=default)
    return p.parse_args()


def dump_outputs(out_dir: Path, out: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics", "style", "exclude"):
        (out_dir / f"{name}.txt").write_text(str(out.get(name, "")), encoding="utf-8")
    keys = (
        "portrait", "lyrics", "style", "exclude", "emotion_focus", "persona_used",
        "selected_ids", "anchor_source_paths", "anchor_song_name", "anchor_chorus_status", "anchor_chorus",
        "review_skipped", "review_decision", "review_reason", "lyrics_changed", "polish_passes", "polish_diffs",
        "platform_adapt_status", "platform_adapt_raw_response",
        "llm_total_input_tokens", "llm_total_output_tokens", "llm_total_calls",
    )
    trace = {k: out.get(k) for k in keys}
    if trace.get("selection_mode") == "empty_pool": print("WARNING: golden_dozen empty, anchor=0", file=sys.stderr)
    (out_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
