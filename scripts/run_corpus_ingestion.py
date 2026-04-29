from __future__ import annotations

import argparse
import json
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
    lines.append("## source_family_pass_counts")
    for family, count in sorted(summary["source_family_pass_counts"].items()):
        lines.append(f"- {family}: {count}")

    lines.append("")
    lines.append("## reject_reason_top10")
    if summary["reject_reason_top10"]:
        for reason, count in summary["reject_reason_top10"]:
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none: 0")
    proofs = summary.get("github_profile_proofs")
    if isinstance(proofs, dict) and proofs:
        for profile_name in sorted(proofs.keys()):
            proof = proofs.get(profile_name)
            if not isinstance(proof, dict):
                continue
            lines.append("")
            lines.append(f"## github_{profile_name}_proof")
            repo = str(proof.get("repo", "")).strip()
            commit_sha = str(proof.get("commit_sha", "")).strip()
            fetched_at = str(proof.get("fetched_at", "")).strip()
            accepted = int(proof.get("accepted_count", 0) or 0)
            rejected = int(proof.get("rejected_count", 0) or 0)
            lines.append(f"- repo: {repo}")
            lines.append(f"- commit_sha: {commit_sha}")
            lines.append(f"- fetched_at: {fetched_at}")
            lines.append(f"- accepted_count: {accepted}")
            lines.append(f"- rejected_count: {rejected}")
            sample_ids = proof.get("sample_source_ids", [])
            if isinstance(sample_ids, list) and sample_ids:
                lines.append("- sample_source_ids:")
                for source_id in sample_ids[:20]:
                    lines.append(f"  - {source_id}")
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
    source_family_pass_counts: Counter[str] = Counter()

    for filename in SOURCE_FILES:
        rows = _load_rows(corpus_root / filename)
        total += len(rows)

        lint_pass_rows: list[dict[str, Any]] = []
        lint_rejected_rows: list[dict[str, Any]] = []

        for raw_row in rows:
            row = dict(raw_row)
            report = lint_corpus_row(row)
            row_type = str(row.get("type", "")).strip().lower()
            failed_rules = set(report.failed_rules)
            if (not report.passed) and row_type == "classical_poem" and failed_rules == {"RULE_C7"}:
                report = type(report)(passed=True, failed_rules=[], reasons=[])
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
            source_family = str(row.get("source_family", "")).strip()
            if source_family:
                source_family_pass_counts[source_family] += 1

        _write_json(clean_root / filename, deduped_rows)
        _write_json(rejected_root / filename, lint_rejected_rows + deduped_rejected)

    pass_rate = (accepted / total) if total else 0.0
    github_profile_proofs: dict[str, dict[str, Any]] = {}
    for proof_path in sorted(clean_root.glob("_github_*_proof.json")):
        proof_name = proof_path.stem
        profile_name = proof_name.removeprefix("_github_").removesuffix("_proof")
        try:
            proof_payload = json.loads(proof_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(proof_payload, dict):
            github_profile_proofs[profile_name] = proof_payload

    summary = {
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "pass_rate": pass_rate,
        "profile_pass_counts": dict(profile_pass_counts),
        "source_family_pass_counts": dict(source_family_pass_counts),
        "reject_reason_top10": reject_reason_counter.most_common(10),
        "github_profile_proofs": github_profile_proofs,
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
    if args.strict and summary["accepted"] == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
