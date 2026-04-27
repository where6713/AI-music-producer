from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Import enrich functions from rule_enrich_classical
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rule_enrich_classical import enrich_row


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill classical rows with rule-based enrich fields")
    parser.add_argument("--input", default="corpus/poetry_classical.json")
    parser.add_argument("--output", default="corpus/poetry_classical.json")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    rows = _load_rows(input_path)
    fixed = []
    
    for row in rows:
        row_type = str(row.get("type", "")).lower()
        if row_type == "classical_poem":
            # Check if already has new fields
            has_new_fields = bool(row.get("emotion_core")) and bool(row.get("archetype"))
            if not has_new_fields:
                row = enrich_row(row)
        fixed.append(row)
    
    output_path.write_text(json.dumps(fixed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fixed {len(fixed)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
