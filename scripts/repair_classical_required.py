from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rule_enrich_classical import enrich_row


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def main() -> int:
    path = Path("corpus/poetry_classical.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    fixed = []
    repaired = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("type", "")).lower() != "classical_poem":
            fixed.append(row)
            continue

        needs_repair = False
        if not isinstance(row.get("emotion_tags"), list) or not row.get("emotion_tags"):
            needs_repair = True
        if not str(row.get("learn_point", "")).strip():
            needs_repair = True
        if not str(row.get("emotion_core", "")).strip():
            needs_repair = True
        if not str(row.get("archetype", "")).strip():
            needs_repair = True
        if not row.get("phonetic_rhythm"):
            needs_repair = True

        if needs_repair:
            repaired += 1
            base = enrich_row(row)
            row = dict(row)
            for key in [
                "emotion_tags",
                "learn_point",
                "emotion_core",
                "archetype",
                "musical_traits",
                "lyric_strategies",
                "core_imagery",
                "phonetic_rhythm",
                "quotability",
            ]:
                val = row.get(key)
                if key in {"emotion_tags", "core_imagery", "lyric_strategies"}:
                    if not isinstance(val, list) or not val:
                        row[key] = base.get(key)
                elif key in {"musical_traits", "phonetic_rhythm"}:
                    if not isinstance(val, dict) or not val:
                        row[key] = base.get(key)
                else:
                    if _is_blank(val):
                        row[key] = base.get(key)

        fixed.append(row)

    path.write_text(json.dumps(fixed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "rows": len(fixed), "repaired": repaired}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
