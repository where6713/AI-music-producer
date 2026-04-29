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


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge_rows_by_source_id(base: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index_by_source_id: dict[str, int] = {}

    def upsert(row: dict[str, Any]) -> None:
        item = dict(row)
        source_id = str(item.get("source_id", "")).strip()
        if not source_id:
            merged.append(item)
            return
        if source_id in index_by_source_id:
            merged[index_by_source_id[source_id]] = item
            return
        index_by_source_id[source_id] = len(merged)
        merged.append(item)

    for row in base:
        upsert(row)
    for row in incoming:
        upsert(row)
    return merged


def _drop_empty_source_family(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("source_family", "")).strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="merge raw golden anchor outputs into main corpus files")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    corpus_root = repo_root / "corpus"
    raw_root = corpus_root / "_raw"

    poetry_main = corpus_root / "poetry_classical.json"
    modern_main = corpus_root / "lyrics_modern_zh.json"
    poetry_raw = raw_root / "golden_anchors_classical.json"
    modern_raw = raw_root / "golden_anchors_modern.json"

    poetry_merged = _merge_rows_by_source_id(_load_rows(poetry_main), _load_rows(poetry_raw))
    modern_merged = _merge_rows_by_source_id(_load_rows(modern_main), _load_rows(modern_raw))
    modern_merged = _drop_empty_source_family(modern_merged)

    _write_rows(poetry_main, poetry_merged)
    _write_rows(modern_main, modern_merged)

    print(
        json.dumps(
            {
                "status": "ok",
                "poetry_total": len(poetry_merged),
                "modern_total": len(modern_merged),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
