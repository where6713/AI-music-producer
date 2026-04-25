from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.corpus_quality_lint import lint_corpus_row


_TIME_TAG_RE = re.compile(r"\[\d{1,2}:\d{1,2}(?:\.\d{1,3})?\]")
_SPACE_RE = re.compile(r"\s+")

_UPLIFT_HINTS = {
    "亮", "光", "晴", "笑", "飞", "梦", "勇", "走", "唱", "跳", "风", "天", "星", "sun", "light", "rise",
}


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}\n{completed.stderr.strip()}")
    return completed.stdout.strip()


def clone_or_refresh_repo(*, owner: str, repo: str, raw_root: Path) -> Path:
    raw_root.mkdir(parents=True, exist_ok=True)
    target = raw_root / f"{owner}__{repo}"
    if not target.exists():
        _run(["git", "clone", "--depth", "1", f"https://github.com/{owner}/{repo}.git", str(target)])
        return target

    _run(["git", "fetch", "origin", "--depth", "1"], cwd=target)
    _run(["git", "reset", "--hard", "origin/HEAD"], cwd=target)
    return target


def get_commit_sha(repo_dir: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], cwd=repo_dir)


def _normalize_lines(text: str) -> list[str]:
    cleaned = _TIME_TAG_RE.sub("", text)
    lines = []
    for raw in cleaned.splitlines():
        line = _SPACE_RE.sub(" ", raw).strip()
        if line:
            lines.append(line)
    return lines


def _looks_uplift(lines: list[str], title: str) -> bool:
    if len(lines) < 4:
        return False
    joined = f"{title} {' '.join(lines)}".lower()
    return any(token in joined for token in _UPLIFT_HINTS)


def _row_from_text(*, owner: str, repo: str, rel_path: Path, text: str) -> dict[str, Any] | None:
    lines = _normalize_lines(text)
    title = rel_path.stem.strip() or rel_path.name
    if not _looks_uplift(lines, title):
        return None

    content = "\n".join(lines)
    source_id = f"github:{owner}/{repo}:{str(rel_path).replace('\\', '/')}"
    return {
        "source_id": source_id,
        "type": "modern_lyric",
        "title": title,
        "emotion_tags": ["uplift", "get-up", "forward"],
        "profile_tag": "uplift_pop",
        "profile_confidence": 0.85,
        "content": content,
        "valence": "positive",
        "learn_point": "学习明亮情绪的动词推进与正向抬升节奏",
        "do_not_copy": "禁止复写来源文本原句与段落顺序",
    }


def _extract_text_candidates(raw_repo: Path) -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []
    for archive in raw_repo.rglob("*.zip"):
        try:
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    inner_path = Path(info.filename)
                    if inner_path.suffix.lower() != ".txt":
                        continue
                    with zf.open(info, "r") as fp:
                        raw = fp.read()
                    text = raw.decode("utf-8", errors="ignore").strip()
                    if not text:
                        continue
                    rel = Path(archive.name) / inner_path
                    candidates.append((rel, text))
        except zipfile.BadZipFile:
            continue

    for path in raw_repo.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue

        suffix = path.suffix.lower()
        rel = path.relative_to(raw_repo)
        if suffix in {".txt", ".lrc", ".md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if text.strip():
                candidates.append((rel, text))
        elif suffix == ".json":
            text = path.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, list):
                for idx, item in enumerate(payload):
                    if not isinstance(item, dict):
                        continue
                    lyric = str(item.get("lyric") or item.get("lyrics") or item.get("text") or "").strip()
                    if not lyric:
                        continue
                    title = str(item.get("title") or item.get("song") or f"item_{idx}")
                    synthetic_rel = rel.parent / f"{rel.stem}__{idx}__{title}.txt"
                    candidates.append((synthetic_rel, lyric))
    return candidates


def build_uplift_pop_rows_from_raw(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> list[dict[str, Any]]:
    rows, _, _ = _build_uplift_pop_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
    )
    return rows


def _build_uplift_pop_rows_with_stats(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    rejected_count = 0
    total_candidates = 0
    for rel_path, text in _extract_text_candidates(raw_repo):
        row = _row_from_text(owner=owner, repo=repo, rel_path=rel_path, text=text)
        if row is None:
            continue
        total_candidates += 1
        lint_report = lint_corpus_row(row, mode="runtime")
        if not lint_report.passed:
            rejected_count += 1
            continue
        digest = hashlib.sha1(row["content"].encode("utf-8")).hexdigest()
        if digest in seen:
            rejected_count += 1
            continue
        seen.add(digest)
        rows.append(row)
        if len(rows) >= target_count:
            break
    return rows, rejected_count, total_candidates


def write_proof_file(
    *,
    proof_path: Path,
    owner: str,
    repo: str,
    commit_sha: str,
    rows: list[dict[str, Any]],
    rejected_count: int,
) -> None:
    sample_ids = [str(row.get("source_id", "")) for row in rows[:20]]
    payload = {
        "repo": f"https://github.com/{owner}/{repo}",
        "commit_sha": commit_sha,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "accepted_count": len(rows),
        "rejected_count": int(rejected_count),
        "sample_source_ids": sample_ids,
    }
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _replace_uplift_rows(main_corpus_path: Path, uplift_rows: list[dict[str, Any]]) -> None:
    if main_corpus_path.exists():
        data = json.loads(main_corpus_path.read_text(encoding="utf-8"))
        existing = [row for row in data if isinstance(row, dict)]
    else:
        existing = []

    kept = [row for row in existing if str(row.get("profile_tag", "")).strip() != "uplift_pop"]
    merged = kept + uplift_rows
    _write_rows(main_corpus_path, merged)


def main() -> int:
    parser = argparse.ArgumentParser(description="ingest real GitHub corpus for uplift_pop(get up)")
    parser.add_argument("--owner", default="dengxiuqi")
    parser.add_argument("--repo", default="Chinese-Lyric-Corpus")
    parser.add_argument("--target-count", type=int, default=220)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--raw-root", default="corpus/_raw/github")
    parser.add_argument("--output", default="corpus/_clean/lyrics_modern_zh_uplift_pop.github.json")
    parser.add_argument("--proof", default="corpus/_clean/_github_uplift_pop_proof.json")
    parser.add_argument("--merge-into-main", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    raw_root = (repo_root / args.raw_root).resolve()
    output_path = (repo_root / args.output).resolve()
    proof_path = (repo_root / args.proof).resolve()

    raw_repo = clone_or_refresh_repo(owner=args.owner, repo=args.repo, raw_root=raw_root)
    commit_sha = get_commit_sha(raw_repo)
    rows, rejected_count, total_candidates = _build_uplift_pop_rows_with_stats(
        raw_repo,
        owner=args.owner,
        repo=args.repo,
        target_count=args.target_count,
    )

    _write_rows(output_path, rows)
    if args.merge_into_main:
        _replace_uplift_rows(repo_root / "corpus/lyrics_modern_zh.json", rows)

    write_proof_file(
        proof_path=proof_path,
        owner=args.owner,
        repo=args.repo,
        commit_sha=commit_sha,
        rows=rows,
        rejected_count=rejected_count,
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "repo": f"{args.owner}/{args.repo}",
                "commit_sha": commit_sha,
                "accepted": len(rows),
                "candidate_rows": total_candidates,
                "filtered_out": rejected_count,
                "target": args.target_count,
                "output": str(output_path),
                "proof": str(proof_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
