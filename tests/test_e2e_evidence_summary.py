from __future__ import annotations

import json
import importlib.util
from pathlib import Path


def _load_summarizer_main() -> object:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "scripts"
        / "summarize_e2e_evidence.py"
    )
    spec = importlib.util.spec_from_file_location("summarize_e2e_evidence", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def test_summarize_e2e_evidence_writes_expected_fields(tmp_path: Path, monkeypatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    run_result = {
        "run_id": "r1",
        "trace_id": "t1",
        "audit_trace": [
            {
                "run_id": "r1",
                "trace_id": "t1",
                "event": "[Grid Loaded]",
                "rule": "grid",
                "decision": "selected",
                "reason_code": "grid_loaded",
            }
        ],
    }
    (run_dir / "run_result.json").write_text(
        json.dumps(run_result, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "score_breakdown.json").write_text(
        json.dumps({"total_score": 9.1}, ensure_ascii=False), encoding="utf-8"
    )
    (run_dir / "ledger.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "run_id": "r1",
                        "trace_id": "t1",
                        "event": "[Montage Hit]",
                        "rule": "montage",
                        "decision": "sampled",
                        "reason_code": "montage_sampled",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "run_id": "r1",
                        "trace_id": "t1",
                        "event": "[Phonetic Check]",
                        "rule": "phonetic",
                        "decision": "fail",
                        "reason_code": "non_open_yunmu",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "run_id": "r1",
                        "trace_id": "t1",
                        "event": "[Cliche Hit]",
                        "rule": "cliche_density",
                        "decision": "rewrite",
                        "reason_code": "cliche_density_exceeded",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    summarize_main = _load_summarizer_main()
    monkeypatch.setattr("sys.argv", ["summarize_e2e_evidence.py", str(run_dir)])
    code = summarize_main()
    assert code == 0

    summary = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == "r1"
    assert summary["trace_id"] == "t1"
    assert summary["score"] == 9.1
    assert summary["event_counts"]["[Grid Loaded]"] >= 1
    assert summary["event_counts"]["[Montage Hit]"] >= 1
    assert summary["event_counts"]["[Phonetic Check]"] >= 1
    assert summary["event_counts"]["[Cliche Hit]"] >= 1
