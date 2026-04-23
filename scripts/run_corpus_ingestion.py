from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.corpus_quality_lint import dedupe_similar_rows, lint_corpus_row


SOURCE_FILES = [
    "lyrics_modern_zh.json",
    "poetry_classical.json",
]

_DIGIT_TO_CN = str.maketrans({
    "0": "零",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
})
_DIGIT_TO_ASCII = str.maketrans({
    "0": "a",
    "1": "b",
    "2": "c",
    "3": "d",
    "4": "e",
    "5": "f",
    "6": "g",
    "7": "h",
    "8": "i",
    "9": "j",
})
_PROFILE_TO_VALENCE = {
    "urban_introspective": "negative",
    "classical_restraint": "neutral",
    "uplift_pop": "positive",
    "club_dance": "positive",
    "ambient_meditation": "neutral",
}
_PROFILE_TO_LEARN_POINT = {
    "urban_introspective": "保留克制语气并用动作推进情绪",
    "classical_restraint": "使用留白与具象意象承载情绪",
    "uplift_pop": "保持明亮节奏并强化动词驱动",
    "club_dance": "突出律动词并维持高能推进",
    "ambient_meditation": "以呼吸感意象维持平静流动",
}


def _clean_text_digits(value: str) -> str:
    return value.translate(_DIGIT_TO_CN)


def _clean_source_id(value: str) -> str:
    normalized = value.translate(_DIGIT_TO_ASCII)
    normalized = re.sub(r"[^a-zA-Z_\-]", "", normalized)
    return normalized.lower()


def _infer_profile_tag(row: dict[str, Any]) -> str:
    explicit = str(row.get("profile_tag", "")).strip()
    if explicit:
        return explicit
    row_type = str(row.get("type", "")).strip().lower()
    tags = [str(x).strip().lower() for x in row.get("emotion_tags", []) if str(x).strip()]
    if row_type == "classical_poem":
        return "classical_restraint"
    if any(tag in {"joy", "sunshine", "brave"} for tag in tags):
        return "uplift_pop"
    if any(tag in {"dance", "nightlife", "club"} for tag in tags):
        return "club_dance"
    if any(tag in {"calm", "meditation", "ambient"} for tag in tags):
        return "ambient_meditation"
    return "urban_introspective"


def _prepare_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    profile_tag = _infer_profile_tag(out)
    source_id = str(out.get("source_id", "")).strip()
    title = str(out.get("title", "")).strip()
    content = str(out.get("content", "")).strip()

    out["profile_tag"] = profile_tag
    out["valence"] = str(out.get("valence", "")).strip() or _PROFILE_TO_VALENCE.get(profile_tag, "neutral")
    out["learn_point"] = str(out.get("learn_point", "")).strip() or _PROFILE_TO_LEARN_POINT.get(profile_tag, "保持具象化并避免模板化复写")
    out["source_id"] = _clean_source_id(source_id) or f"sample_{profile_tag}"
    out["title"] = _clean_text_digits(title)
    out["content"] = _clean_text_digits(content)
    return out


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Corpus Ingestion Report",
        "",
        f"- total: {summary['total']}",
        f"- accepted: {summary['accepted']}",
        f"- rejected: {summary['rejected']}",
        f"- pass_rate: {summary['pass_rate']:.2%}",
        "",
        "## profile_pass_counts",
    ]
    for profile, count in sorted(summary["profile_pass_counts"].items()):
        lines.append(f"- {profile}: {count}")

    lines.append("")
    lines.append("## reject_reason_top10")
    if summary["reject_reason_top10"]:
        for reason, count in summary["reject_reason_top10"]:
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none: 0")
    lines.append("")
    return "\n".join(lines)


def run_ingestion(*, repo_root: Path, strict: bool) -> dict[str, Any]:
    corpus_root = repo_root / "corpus"
    clean_root = corpus_root / "_clean"
    rejected_root = corpus_root / "_rejected"

    total = 0
    accepted = 0
    rejected = 0
    reject_reason_counter: Counter[str] = Counter()
    profile_pass_counts: Counter[str] = Counter()

    for filename in SOURCE_FILES:
        rows = _load_rows(corpus_root / filename)
        total += len(rows)

        lint_pass_rows: list[dict[str, Any]] = []
        lint_rejected_rows: list[dict[str, Any]] = []

        for raw_row in rows:
            row = _prepare_row(raw_row)
            report = lint_corpus_row(row)
            if report.passed:
                lint_pass_rows.append(row)
            else:
                marked = dict(row)
                marked["_rejected_rules"] = report.failed_rules
                marked["_rejected_reasons"] = report.reasons
                lint_rejected_rows.append(marked)
                for code in report.failed_rules:
                    reject_reason_counter[code] += 1

        deduped_rows, deduped_rejected = dedupe_similar_rows(lint_pass_rows)
        for row in deduped_rejected:
            for code in row.get("_rejected_rules", []):
                reject_reason_counter[str(code)] += 1

        accepted += len(deduped_rows)
        rejected += len(lint_rejected_rows) + len(deduped_rejected)

        for row in deduped_rows:
            profile = str(row.get("profile_tag", "")).strip()
            if profile:
                profile_pass_counts[profile] += 1

        _write_json(clean_root / filename, deduped_rows)
        _write_json(rejected_root / filename, lint_rejected_rows + deduped_rejected)

    pass_rate = (accepted / total) if total else 0.0
    summary = {
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "pass_rate": pass_rate,
        "profile_pass_counts": dict(profile_pass_counts),
        "reject_reason_top10": reject_reason_counter.most_common(10),
    }

    report_text = _render_report(summary)
    (corpus_root / "_ingestion_report.md").write_text(report_text, encoding="utf-8")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="run corpus ingestion lint")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any row rejected")
    args = parser.parse_args()

    summary = run_ingestion(repo_root=Path.cwd(), strict=args.strict)
    print(
        json.dumps(
            {
                "status": "ok",
                "strict": args.strict,
                "total": summary["total"],
                "accepted": summary["accepted"],
                "rejected": summary["rejected"],
            },
            ensure_ascii=False,
        )
    )
    if args.strict and summary["rejected"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
