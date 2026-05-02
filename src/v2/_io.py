from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from ._trace_schema import make_trace


def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    for flag, default in [("--intent", ""), ("--ref-audio", ""), ("--index", "corpus/_index.json"), ("--out", "out/runs/smoke")]:
        p.add_argument(flag, default=default)
    return p.parse_args()


def dump_outputs(out_dir: Path, out: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics", "style", "exclude"):
        (out_dir / f"{name}.txt").write_text(str(out.get(name, "")), encoding="utf-8")
    trace = make_trace(out)
    if trace.get("selection_mode") == "empty_pool": print("WARNING: golden_dozen empty, anchor=0", file=sys.stderr)
    (out_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
