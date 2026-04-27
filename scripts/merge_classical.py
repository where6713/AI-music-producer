from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge new classical rows into poetry_classical.json")
    parser.add_argument("--main", default="corpus/poetry_classical.json")
    parser.add_argument("--new", default="corpus/_raw/new_classical_rule_enriched.json")
    parser.add_argument("--output", default="corpus/poetry_classical.json")
    args = parser.parse_args()
    
    main_path = Path(args.main)
    new_path = Path(args.new)
    output_path = Path(args.output)
    
    main_rows = _load_rows(main_path)
    new_rows = _load_rows(new_path)
    
    # Deduplicate by content hash
    seen_hashes = set()
    deduped_main = []
    for row in main_rows:
        h = hash(str(row.get("content", "")).strip())
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped_main.append(row)
    
    deduped_new = []
    for row in new_rows:
        h = hash(str(row.get("content", "")).strip())
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduped_new.append(row)
    
    merged = deduped_main + deduped_new
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"Merged: {len(deduped_main)} (main) + {len(deduped_new)} (new) = {len(merged)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
