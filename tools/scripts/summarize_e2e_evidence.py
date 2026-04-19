from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_EVENTS = [
    "[Grid Loaded]",
    "[Montage Hit]",
    "[Phonetic Check]",
    "[Cliche Hit]",
]


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _event_sample(
    events: list[dict[str, object]],
    event_name: str,
) -> dict[str, object] | None:
    for item in events:
        if item.get("event") == event_name:
            return item
    return None


def _load_ledger_events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/scripts/summarize_e2e_evidence.py <run_dir>")
        return 2

    run_dir = Path(sys.argv[1]).expanduser().resolve()
    run_result_path = run_dir / "run_result.json"
    score_path = run_dir / "score_breakdown.json"

    if not run_result_path.exists():
        print(f"Missing run_result.json: {run_result_path}")
        return 2
    if not score_path.exists():
        print(f"Missing score_breakdown.json: {score_path}")
        return 2

    run_result = _load_json(run_result_path)
    score = _load_json(score_path)

    run_id = str(run_result.get("run_id", ""))
    trace_id = str(run_result.get("trace_id", ""))
    total_score = score.get("total_score", 0)

    audit_trace = run_result.get("audit_trace", [])
    events = [x for x in audit_trace if isinstance(x, dict)] if isinstance(audit_trace, list) else []
    ledger_events = _load_ledger_events(run_dir / "ledger.jsonl")
    merged_events = events + ledger_events

    event_counts: dict[str, int] = {}
    event_samples: dict[str, dict[str, object]] = {}
    for ev in REQUIRED_EVENTS:
        hits = [x for x in merged_events if x.get("event") == ev]
        event_counts[ev] = len(hits)
        sample = _event_sample(merged_events, ev)
        if sample is not None:
            event_samples[ev] = {
                "run_id": sample.get("run_id", ""),
                "trace_id": sample.get("trace_id", ""),
                "event": sample.get("event", ""),
                "rule": sample.get("rule", ""),
                "decision": sample.get("decision", ""),
                "reason_code": sample.get("reason_code", ""),
            }

    summary = {
        "run_id": run_id,
        "trace_id": trace_id,
        "score": total_score,
        "required_events": REQUIRED_EVENTS,
        "event_counts": event_counts,
        "event_samples": event_samples,
        "source": {
            "run_result": str(run_result_path),
            "score_breakdown": str(score_path),
            "ledger": str(run_dir / "ledger.jsonl"),
        },
    }

    out_path = run_dir / "evidence_summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
