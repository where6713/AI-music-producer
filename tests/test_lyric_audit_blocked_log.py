from __future__ import annotations

import json
import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from producer_tools.business import lyric_architect


def test_blocked_log_emitted_on_cliche_blacklist_hit(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"

    result = lyric_architect.run(
        {
            "intent": "星辰大海 岁月静好",
            "reference_dna": {"structure": [{"label": "verse", "energy": 0.4}]},
            "use_llm": True,
            "llm_adapter": lambda _: {"lines": ["星辰大海", "岁月静好"]},
            "max_rewrite_iterations": 1,
            "negative_lexicon": ["星辰大海", "岁月静好"],
            "run_id": "blocked-test",
            "trace_id": "blocked-test",
            "ledger_path": str(ledger),
            "peak_positions": [],
            "long_note_positions": [],
        }
    )

    assert result["ok"] is False
    text = ledger.read_text(encoding="utf-8")
    rows = [json.loads(x) for x in text.splitlines() if x.strip()]
    blocked = [x for x in rows if x.get("event") == "[Blocked]"]
    assert blocked
    assert blocked[0].get("reason_code") == "cliche_blacklist_blocked"
