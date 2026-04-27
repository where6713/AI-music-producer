from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_shijing(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"{path} must be a JSON list")
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        content_lines = item.get("content", [])
        if not isinstance(content_lines, list):
            continue
        content = "\n".join(str(x).strip() for x in content_lines if str(x).strip())
        if not content or len(content) < 12:
            continue
        title = str(item.get("title", "")).strip()
        chapter = str(item.get("chapter", "")).strip()
        section = str(item.get("section", "")).strip()
        source_id = f"github:local/shijing.json#{idx}"
        rows.append({
            "source_id": source_id,
            "type": "classical_poem",
            "source_family": "shijing",
            "title": title,
            "author": f"{chapter}·{section}" if chapter and section else chapter or section or "佚名",
            "content": content,
            "era": "先秦",
            "profile_tag": "classical_restraint",
            "valence": "mixed",
            "learn_point": "",
            "emotion_tags": [],
        })
    return rows


def parse_nalan(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"{path} must be a JSON list")
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        para_lines = item.get("para", [])
        if not isinstance(para_lines, list):
            continue
        content = "\n".join(str(x).strip() for x in para_lines if str(x).strip())
        if not content or len(content) < 12:
            continue
        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip() or "纳兰性德"
        source_id = f"github:local/nalan.json#{idx}"
        rows.append({
            "source_id": source_id,
            "type": "classical_poem",
            "source_family": "nalan",
            "title": title,
            "author": author,
            "content": content,
            "era": "清",
            "profile_tag": "classical_restraint",
            "valence": "mixed",
            "learn_point": "",
            "emotion_tags": [],
        })
    return rows


def parse_shuimotangshi(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"{path} must be a JSON list")
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        paragraphs = item.get("paragraphs", [])
        if not isinstance(paragraphs, list):
            continue
        content = "\n".join(str(x).strip() for x in paragraphs if str(x).strip())
        if not content or len(content) < 12:
            continue
        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip() or "佚名"
        source_id = f"github:local/shuimotangshi.json#{idx}"
        rows.append({
            "source_id": source_id,
            "type": "classical_poem",
            "source_family": "tang_shui_mo",
            "title": title,
            "author": author,
            "content": content,
            "era": "唐",
            "profile_tag": "classical_restraint",
            "valence": "mixed",
            "learn_point": "",
            "emotion_tags": [],
        })
    return rows


def parse_songci300(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError(f"{path} must be a JSON list")
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        paragraphs = item.get("paragraphs", [])
        if not isinstance(paragraphs, list):
            continue
        content = "\n".join(str(x).strip() for x in paragraphs if str(x).strip())
        if not content or len(content) < 12:
            continue
        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip() or "佚名"
        rhythmic = str(item.get("rhythmic", "")).strip()
        if rhythmic and title:
            title = f"{rhythmic}·{title}"
        source_id = f"github:local/songci300.json#{idx}"
        rows.append({
            "source_id": source_id,
            "type": "classical_poem",
            "source_family": "song_ci_300",
            "title": title,
            "author": author,
            "content": content,
            "era": "宋",
            "profile_tag": "classical_restraint",
            "valence": "mixed",
            "learn_point": "",
            "emotion_tags": [],
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest new classical poetry JSONs into unified rows")
    parser.add_argument("--output", default="corpus/_raw/new_classical_unenriched.json")
    args = parser.parse_args()

    raw_dir = Path("corpus/_raw/github")
    all_rows: list[dict[str, Any]] = []

    shijing_path = raw_dir / "shijing.json"
    if shijing_path.exists():
        rows = parse_shijing(shijing_path)
        print(f"shijing: {len(rows)} rows")
        all_rows.extend(rows)
    else:
        print("shijing.json not found")

    nalan_path = raw_dir / "纳兰性德诗集.json"
    if nalan_path.exists():
        rows = parse_nalan(nalan_path)
        print(f"nalan: {len(rows)} rows")
        all_rows.extend(rows)
    else:
        print("纳兰性德诗集.json not found")

    tangshi_path = raw_dir / "shuimotangshi.json"
    if tangshi_path.exists():
        rows = parse_shuimotangshi(tangshi_path)
        print(f"shuimotangshi: {len(rows)} rows")
        all_rows.extend(rows)
    else:
        print("shuimotangshi.json not found")

    songci_path = raw_dir / "宋词三百首.json"
    if songci_path.exists():
        rows = parse_songci300(songci_path)
        print(f"songci300: {len(rows)} rows")
        all_rows.extend(rows)
    else:
        print("宋词三百首.json not found")

    output_path = Path(args.output)
    _write_json(output_path, all_rows)
    print(f"\nTotal rows written: {len(all_rows)} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
