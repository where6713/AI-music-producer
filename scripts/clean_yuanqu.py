from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


IMAGERY_KEYWORDS = {
    "月",
    "风",
    "花",
    "雪",
    "云",
    "雨",
    "秋",
    "春",
    "山",
    "水",
    "江",
    "夜",
    "梦",
    "柳",
    "梅",
    "雁",
    "烟",
    "霜",
    "灯",
    "酒",
    "愁",
    "相思",
    "归",
}

EXCLUDED_THEME_KEYWORDS = {
    "怀古",
    "咏史",
    "边塞",
    "从军",
    "征",
    "战",
    "胡",
    "沙场",
    "闺怨",
    "宫怨",
    "羁旅",
    "旅",
    "送别",
    "离别",
}

COARSE_KEYWORDS = {
    "牛粪",
    "婆娘",
    "这厮",
    "贼",
    "骂",
    "脏",
}

CLASSIC_AUTHORS = {
    "马致远",
    "白朴",
    "关汉卿",
    "张可久",
    "乔吉",
    "贯云石",
    "徐再思",
    "卢挚",
    "刘致",
    "倪瓒",
    "赵善庆",
    "查德卿",
}


def _load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("input corpus must be a JSON list")
    return [x for x in data if isinstance(x, dict)]


def _is_yuanqu(row: dict[str, Any]) -> bool:
    return "yuanqu" in str(row.get("source_id", "")).lower()


def _should_reject(row: dict[str, Any]) -> tuple[bool, str]:
    title = str(row.get("title", "")).strip()
    author = str(row.get("author", "")).strip()
    content = str(row.get("content", "")).strip()
    joined = f"{title} {content}"

    if not author or author == "无名氏":
        return True, "anonymous_or_missing_author"
    if not content or len(content) < 12:
        return True, "too_short"
    if len(content) > 180:
        return True, "too_long"
    if "(" in content or "（" in content or "云)" in content or "云）" in content:
        return True, "stage_direction"
    if any(k in joined for k in COARSE_KEYWORDS):
        return True, "coarse_language"
    if any(k in title for k in EXCLUDED_THEME_KEYWORDS):
        return True, "excluded_theme"
    if any(k in content for k in EXCLUDED_THEME_KEYWORDS):
        return True, "excluded_theme"
    return False, ""


def _score_row(row: dict[str, Any]) -> int:
    title = str(row.get("title", "")).strip()
    author = str(row.get("author", "")).strip()
    content = str(row.get("content", "")).strip()
    joined = f"{title} {content}"

    score = 0
    if author in CLASSIC_AUTHORS:
        score += 5
    score += sum(1 for kw in IMAGERY_KEYWORDS if kw in joined)

    line_count = len([ln for ln in content.splitlines() if ln.strip()])
    if 2 <= line_count <= 8:
        score += 3
    if 20 <= len(content) <= 120:
        score += 2

    if "天净沙" in title or "水仙子" in title or "折桂令" in title or "寿阳曲" in title:
        score += 2
    return score


def clean_yuanqu(rows: list[dict[str, Any]], *, target_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    yuanqu_rows = [r for r in rows if _is_yuanqu(r)]
    other_rows = [r for r in rows if not _is_yuanqu(r)]

    survivors: list[tuple[int, dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []

    for row in yuanqu_rows:
        reject, reason = _should_reject(row)
        if reject:
            dropped = dict(row)
            dropped["_rejected_reason"] = reason
            rejected.append(dropped)
            continue
        survivors.append((_score_row(row), row))

    survivors.sort(key=lambda item: item[0], reverse=True)
    kept_yuanqu = [row for _, row in survivors[:target_count]]

    for _, row in survivors[target_count:]:
        dropped = dict(row)
        dropped["_rejected_reason"] = "below_top_score_cutoff"
        rejected.append(dropped)

    final_rows = kept_yuanqu + other_rows
    return final_rows, rejected


def main() -> int:
    parser = argparse.ArgumentParser(description="Trim yuanqu rows in classical corpus")
    parser.add_argument("--input", default="corpus/poetry_classical.json")
    parser.add_argument("--output", default="corpus/poetry_classical.json")
    parser.add_argument("--rejected", default="corpus/_rejected/yuanqu_pruned.json")
    parser.add_argument("--target-count", type=int, default=200)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rejected_path = Path(args.rejected)

    rows = _load_rows(input_path)
    original_yuanqu = sum(1 for r in rows if _is_yuanqu(r))
    final_rows, rejected = clean_yuanqu(rows, target_count=max(1, args.target_count))
    final_yuanqu = sum(1 for r in final_rows if _is_yuanqu(r))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(final_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    rejected_path.write_text(json.dumps(rejected, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "original_total": len(rows),
                "final_total": len(final_rows),
                "yuanqu_before": original_yuanqu,
                "yuanqu_after": final_yuanqu,
                "rejected_count": len(rejected),
                "output": str(output_path),
                "rejected": str(rejected_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
