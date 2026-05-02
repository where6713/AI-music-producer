from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--intent", default="")
    p.add_argument("--ref-audio", default="")
    p.add_argument("--index", default="corpus/_index.json")
    p.add_argument("--out", default="out/runs/smoke")
    return p.parse_args()


def dump_outputs(out_dir: Path, out: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lyrics.txt").write_text(str(out.get("lyrics", "")), encoding="utf-8")
    (out_dir / "style.txt").write_text(str(out.get("style", "")), encoding="utf-8")
    (out_dir / "exclude.txt").write_text(str(out.get("exclude", "")), encoding="utf-8")
    trace = {k: out.get(k) for k in (
        "portrait", "motive", "hook_seed", "selected_ids", "anchor_source_paths", "quality_gate_failed", "selection_mode", "review_notes",
        "recalled_pool_size", "golden_refs_used", "pass1_selected_ids_count",
        "retry_count", "llm_total_calls", "llm_total_input_tokens", "llm_total_output_tokens",
    )}
    if trace.get("selection_mode") == "empty_pool":
        print("WARNING: golden_dozen empty, anchor=0", file=sys.stderr)
    (out_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
