from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _emotion_tags_from_core(emotion_core: str, archetype: str) -> list[str]:
    tags = []
    
    # Map emotion_core to tags
    if "哀愁" in emotion_core or "悲伤" in emotion_core:
        tags.extend(["melancholy", "longing"])
    if "怅惘" in emotion_core or "求而不得" in emotion_core:
        tags.extend(["wistful", "yearning"])
    if "孤独" in emotion_core or "独处" in emotion_core:
        tags.extend(["solitude", "introspective"])
    if "虚无" in emotion_core or "时间" in emotion_core:
        tags.extend(["transience", "existential"])
    if "恬淡" in emotion_core or "静默" in emotion_core:
        tags.extend(["serene", "quiet"])
    if "微小" in emotion_core or "确幸" in emotion_core:
        tags.extend(["tender", "delicate"])
    if "释然" in emotion_core or "豁达" in emotion_core:
        tags.extend(["liberation", "acceptance"])
    if "理想" in emotion_core or "燃烧" in emotion_core:
        tags.extend(["aspiration", "fiery"])
    if "沉溺" in emotion_core or "逃避" in emotion_core:
        tags.extend(["escape", "intoxication"])
    if "撕裂" in emotion_core or "幻想" in emotion_core:
        tags.extend(["dreamlike", "fractured"])
    
    # Map archetype to aesthetic tags
    archetype_map = {
        "失乐园": ["nostalgia", "loss"],
        "浮士德": ["ambition", "restless"],
        "西西弗斯": ["resilience", "cyclical"],
        "普罗米修斯": ["sacrifice", "elevation"],
        "纳西索斯": ["self-reflection", "mirror"],
        "俄耳甫斯": ["art", "transcendence"],
    }
    if archetype in archetype_map:
        tags.extend(archetype_map[archetype])
    
    # Deduplicate and limit
    seen = set()
    result = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result[:5]


def main() -> int:
    p = Path("corpus/poetry_classical.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    
    fixed_count = 0
    for row in data:
        if isinstance(row, dict) and str(row.get("type", "")).lower() == "classical_poem":
            emotion_tags = row.get("emotion_tags")
            if not isinstance(emotion_tags, list) or len(emotion_tags) == 0:
                core = str(row.get("emotion_core", ""))
                archetype = str(row.get("archetype", ""))
                row["emotion_tags"] = _emotion_tags_from_core(core, archetype)
                fixed_count += 1
    
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fixed emotion_tags for {fixed_count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
