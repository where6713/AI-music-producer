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

_URBAN_INTROSPECTIVE_HINTS = {
    "夜", "深夜", "凌晨", "地铁", "街口", "手机", "消息", "删", "草稿", "回忆", "沉默", "没有", "不敢", "停", "口袋",
}

_CLUB_DANCE_HINTS = {
    "跳", "舞", "摇", "燃", "夜", "节奏", "鼓点", "拍", "hands", "dance", "beat", "club",
}

_AMBIENT_MEDITATION_HINTS = {
    "风", "月", "云", "水", "呼吸", "静", "慢", "空", "夜", "light", "calm", "breathe", "still",
}

_CLASSICAL_HINTS = {
    "月", "风", "山", "江", "云", "雨", "夜", "思", "归", "秋", "春", "寒", "梦", "霜", "柳",
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


def _looks_urban_introspective(lines: list[str], title: str) -> bool:
    if len(lines) < 4:
        return False
    joined = f"{title} {' '.join(lines)}".lower()
    return any(token in joined for token in _URBAN_INTROSPECTIVE_HINTS)


def _looks_club_dance(lines: list[str], title: str) -> bool:
    if len(lines) < 4:
        return False
    joined = f"{title} {' '.join(lines)}".lower()
    return any(token in joined for token in _CLUB_DANCE_HINTS)


def _looks_ambient_meditation(lines: list[str], title: str) -> bool:
    if len(lines) < 4:
        return False
    joined = f"{title} {' '.join(lines)}".lower()
    return any(token in joined for token in _AMBIENT_MEDITATION_HINTS)


def _hint_score(text: str, hints: set[str]) -> int:
    score = 0
    for token in hints:
        if token in text:
            score += 1
    return score


def _profile_signal_score(profile: str, text: str) -> int:
    if profile == "uplift_pop":
        return _hint_score(text, _UPLIFT_HINTS)
    if profile == "urban_introspective":
        return _hint_score(text, _URBAN_INTROSPECTIVE_HINTS)
    if profile == "club_dance":
        return _hint_score(text, _CLUB_DANCE_HINTS)
    if profile == "ambient_meditation":
        return _hint_score(text, _AMBIENT_MEDITATION_HINTS)
    return 0


def _profile_signal_evidence(profile: str, text: str) -> tuple[int, list[str]]:
    if profile == "uplift_pop":
        hints = _UPLIFT_HINTS
    elif profile == "urban_introspective":
        hints = _URBAN_INTROSPECTIVE_HINTS
    elif profile == "club_dance":
        hints = _CLUB_DANCE_HINTS
    elif profile == "ambient_meditation":
        hints = _AMBIENT_MEDITATION_HINTS
    else:
        hints = set()
    matched = sorted([token for token in hints if token in text])
    return len(matched), matched


def _looks_classical(lines: list[str], title: str) -> bool:
    if len(lines) < 2:
        return False
    joined = f"{title} {' '.join(lines)}"
    return any(token in joined for token in _CLASSICAL_HINTS)


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


def _row_from_text_urban_introspective(*, owner: str, repo: str, rel_path: Path, text: str) -> dict[str, Any] | None:
    lines = _normalize_lines(text)
    title = rel_path.stem.strip() or rel_path.name
    if not _looks_urban_introspective(lines, title):
        return None

    content = "\n".join(lines)
    source_id = f"github:{owner}/{repo}:{str(rel_path).replace('\\', '/')}"
    return {
        "source_id": source_id,
        "type": "modern_lyric",
        "title": title,
        "emotion_tags": ["breakup", "late-night", "self-control"],
        "profile_tag": "urban_introspective",
        "profile_confidence": 0.85,
        "content": content,
        "valence": "negative",
        "learn_point": "学习克制表达中的动作推进与夜景叙事锚点",
        "do_not_copy": "禁止复写来源文本原句与段落顺序",
    }


def _row_from_text_club_dance(*, owner: str, repo: str, rel_path: Path, text: str) -> dict[str, Any] | None:
    lines = _normalize_lines(text)
    title = rel_path.stem.strip() or rel_path.name
    if not _looks_club_dance(lines, title):
        return None

    content = "\n".join(lines)
    source_id = f"github:{owner}/{repo}:{str(rel_path).replace('\\', '/')}"
    return {
        "source_id": source_id,
        "type": "modern_lyric",
        "title": title,
        "emotion_tags": ["dance", "release", "high-energy"],
        "profile_tag": "club_dance",
        "profile_confidence": 0.85,
        "content": content,
        "valence": "positive",
        "learn_point": "学习短句动词驱动与节奏重复，强化身体感与拍点",
        "do_not_copy": "禁止复写来源文本原句与段落顺序",
    }


def _row_from_text_ambient_meditation(*, owner: str, repo: str, rel_path: Path, text: str) -> dict[str, Any] | None:
    lines = _normalize_lines(text)
    title = rel_path.stem.strip() or rel_path.name
    if not _looks_ambient_meditation(lines, title):
        return None

    content = "\n".join(lines)
    source_id = f"github:{owner}/{repo}:{str(rel_path).replace('\\', '/')}"
    return {
        "source_id": source_id,
        "type": "modern_lyric",
        "title": title,
        "emotion_tags": ["calm", "healing", "meditation"],
        "profile_tag": "ambient_meditation",
        "profile_confidence": 0.85,
        "content": content,
        "valence": "neutral",
        "learn_point": "学习静态循环与自然意象并置，控制叙事推进",
        "do_not_copy": "禁止复写来源文本原句与段落顺序",
    }


def _row_from_poem(
    *,
    owner: str,
    repo: str,
    rel_path: Path,
    title: str,
    author: str,
    paragraphs: list[str],
    index: int,
) -> dict[str, Any] | None:
    lines = [_SPACE_RE.sub(" ", str(x)).strip() for x in paragraphs if str(x).strip()]
    if not _looks_classical(lines, title):
        return None
    content = "\n".join(lines)
    source_id = f"github:{owner}/{repo}:{str(rel_path).replace('\\', '/')}#{index}"
    return {
        "source_id": source_id,
        "type": "classical_poem",
        "title": title,
        "author": author,
        "emotion_tags": ["nostalgia", "restraint", "imagery"],
        "profile_tag": "classical_restraint",
        "profile_confidence": 0.9,
        "content": content,
        "valence": "neutral",
        "learn_point": "学习意象并置与留白表达，避免直白抒情",
        "do_not_copy": "禁止复写来源文本原句与意象排列顺序",
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


def _extract_poem_candidates(raw_repo: Path) -> list[tuple[Path, str, str, list[str], int]]:
    candidates: list[tuple[Path, str, str, list[str], int]] = []
    for path in raw_repo.rglob("*.json"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        rel = path.relative_to(raw_repo)
        for idx, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            author = str(item.get("author") or item.get("name") or "unknown").strip()
            paragraphs = item.get("paragraphs")
            if not title or not isinstance(paragraphs, list):
                continue
            lines = [str(x).strip() for x in paragraphs if str(x).strip()]
            if not lines:
                continue
            candidates.append((rel, title, author, lines, idx))
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


def build_urban_introspective_rows_from_raw(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> list[dict[str, Any]]:
    rows, _, _ = _build_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
        row_factory=_row_from_text_urban_introspective,
    )
    return rows


def build_classical_restraint_rows_from_raw(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> list[dict[str, Any]]:
    rows, _, _ = _build_classical_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
    )
    return rows


def build_club_dance_rows_from_raw(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> list[dict[str, Any]]:
    rows, _, _ = _build_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
        row_factory=_row_from_text_club_dance,
    )
    return rows


def build_ambient_meditation_rows_from_raw(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> list[dict[str, Any]]:
    rows, _, _ = _build_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
        row_factory=_row_from_text_ambient_meditation,
    )
    return rows


def build_modern_disjoint_rows_from_raw(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    targets: dict[str, int],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    profile_order = [
        "urban_introspective",
        "club_dance",
        "ambient_meditation",
        "uplift_pop",
    ]
    row_factory_map = {
        "uplift_pop": _row_from_text,
        "urban_introspective": _row_from_text_urban_introspective,
        "club_dance": _row_from_text_club_dance,
        "ambient_meditation": _row_from_text_ambient_meditation,
    }

    rows_by_profile: dict[str, list[dict[str, Any]]] = {
        profile: [] for profile in profile_order
    }
    seen_source_ids: set[str] = set()
    stats = {
        "candidate_rows": 0,
        "filtered_out": 0,
        "duplicate_source_id": 0,
        "ambiguous_profile": 0,
        "low_signal": 0,
    }

    def _all_targets_met() -> bool:
        for profile in profile_order:
            if len(rows_by_profile[profile]) < int(targets.get(profile, 0)):
                return False
        return True

    for rel_path, text in _extract_text_candidates(raw_repo):
        if _all_targets_met():
            break

        joined = f"{rel_path.stem} {_SPACE_RE.sub(' ', text)}".lower()
        profile_evidence: dict[str, tuple[int, list[str]]] = {
            profile: _profile_signal_evidence(profile, joined)
            for profile in profile_order
        }
        candidates: list[tuple[str, dict[str, Any], int]] = []
        for profile in profile_order:
            if len(rows_by_profile[profile]) >= int(targets.get(profile, 0)):
                continue
            factory = row_factory_map[profile]
            row = factory(owner=owner, repo=repo, rel_path=rel_path, text=text)
            if row is None:
                continue
            score = profile_evidence[profile][0]
            candidates.append((profile, row, score))

        if not candidates:
            continue

        stats["candidate_rows"] += 1
        candidates.sort(
            key=lambda x: (
                x[2],
                -len(rows_by_profile[x[0]]) / max(int(targets.get(x[0], 1)), 1),
                -profile_order.index(x[0]),
            ),
            reverse=True,
        )
        profile, chosen, top_score = candidates[0]
        scored = sorted(
            [(name, score) for name, _row, score in candidates],
            key=lambda x: x[1],
            reverse=True,
        )
        second_score = scored[1][1] if len(scored) > 1 else 0

        if top_score < 2:
            stats["low_signal"] += 1
            stats["filtered_out"] += 1
            continue
        if second_score > 0 and (top_score - second_score) <= 1:
            stats["ambiguous_profile"] += 1
            stats["filtered_out"] += 1
            continue

        chosen = dict(chosen)
        source_id = str(chosen.get("source_id", ""))
        if source_id in seen_source_ids:
            stats["duplicate_source_id"] += 1
            continue

        lint_report = lint_corpus_row(chosen, mode="runtime")
        if not lint_report.passed:
            stats["filtered_out"] += 1
            continue

        matched = profile_evidence.get(profile, (0, []))[1]
        chosen["classification"] = {
            "method": "hint_scoring_disjoint_v2",
            "selected_profile": profile,
            "top_score": int(top_score),
            "second_score": int(second_score),
            "matched_hints": matched,
        }

        seen_source_ids.add(source_id)
        rows_by_profile[profile].append(chosen)

    return rows_by_profile, stats


def _build_rows_with_stats(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
    row_factory: Any,
) -> tuple[list[dict[str, Any]], int, int]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    rejected_count = 0
    total_candidates = 0
    for rel_path, text in _extract_text_candidates(raw_repo):
        row = row_factory(owner=owner, repo=repo, rel_path=rel_path, text=text)
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


def _build_uplift_pop_rows_with_stats(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> tuple[list[dict[str, Any]], int, int]:
    return _build_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
        row_factory=_row_from_text,
    )


def _build_urban_introspective_rows_with_stats(
    raw_repo: Path,
    *,
    owner: str,
    repo: str,
    target_count: int,
) -> tuple[list[dict[str, Any]], int, int]:
    return _build_rows_with_stats(
        raw_repo,
        owner=owner,
        repo=repo,
        target_count=target_count,
        row_factory=_row_from_text_urban_introspective,
    )


def _build_classical_rows_with_stats(
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
    for rel_path, title, author, paragraphs, idx in _extract_poem_candidates(raw_repo):
        row = _row_from_poem(
            owner=owner,
            repo=repo,
            rel_path=rel_path,
            title=title,
            author=author,
            paragraphs=paragraphs,
            index=idx,
        )
        if row is None:
            continue
        total_candidates += 1
        lint_report = lint_corpus_row(row, mode="runtime")
        failed_rules = set(lint_report.failed_rules)
        # Classical rows can be verb-sparse by style; keep other hard checks.
        if failed_rules and failed_rules != {"RULE_C7"}:
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


def _replace_classical_rows(main_corpus_path: Path, classical_rows: list[dict[str, Any]]) -> None:
    if main_corpus_path.exists():
        data = json.loads(main_corpus_path.read_text(encoding="utf-8"))
        existing = [row for row in data if isinstance(row, dict)]
    else:
        existing = []

    kept = [row for row in existing if str(row.get("profile_tag", "")).strip() != "classical_restraint"]
    merged = kept + classical_rows
    _write_rows(main_corpus_path, merged)


def main() -> int:
    parser = argparse.ArgumentParser(description="ingest real GitHub corpus by profile")
    parser.add_argument("--owner", default="dengxiuqi")
    parser.add_argument("--repo", default="Chinese-Lyric-Corpus")
    parser.add_argument("--target-count", type=int, default=220)
    parser.add_argument(
        "--profile",
        choices=[
            "uplift_pop",
            "urban_introspective",
            "classical_restraint",
            "club_dance",
            "ambient_meditation",
            "all_modern",
        ],
        default="uplift_pop",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--raw-root", default="corpus/_raw/github")
    parser.add_argument("--output", default="")
    parser.add_argument("--proof", default="")
    parser.add_argument("--merge-into-main", action="store_true")
    parser.add_argument("--uplift-target", type=int, default=500)
    parser.add_argument("--urban-target", type=int, default=260)
    parser.add_argument("--club-target", type=int, default=200)
    parser.add_argument("--ambient-target", type=int, default=180)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    raw_root = (repo_root / args.raw_root).resolve()
    raw_repo = clone_or_refresh_repo(owner=args.owner, repo=args.repo, raw_root=raw_root)
    commit_sha = get_commit_sha(raw_repo)
    if args.profile == "all_modern":
        targets = {
            "uplift_pop": int(args.uplift_target),
            "urban_introspective": int(args.urban_target),
            "club_dance": int(args.club_target),
            "ambient_meditation": int(args.ambient_target),
        }
        rows_by_profile, stats = build_modern_disjoint_rows_from_raw(
            raw_repo,
            owner=args.owner,
            repo=args.repo,
            targets=targets,
        )
        total_candidates = int(stats.get("candidate_rows", 0))
        rejected_count = int(stats.get("filtered_out", 0)) + int(stats.get("duplicate_source_id", 0))

        _write_modern_outputs_and_proofs(
            repo_root=repo_root,
            owner=args.owner,
            repo=args.repo,
            commit_sha=commit_sha,
            rows_by_profile=rows_by_profile,
            rejected_count=rejected_count,
        )
        if args.merge_into_main:
            _replace_all_modern_rows(repo_root / "corpus/lyrics_modern_zh.json", rows_by_profile)

        all_rows = []
        for key in ["uplift_pop", "urban_introspective", "club_dance", "ambient_meditation"]:
            all_rows.extend(list(rows_by_profile.get(key, [])))

        summary_path = repo_root / "corpus/_clean/_github_all_modern_disjoint_summary.json"
        summary_payload = {
            "repo": f"https://github.com/{args.owner}/{args.repo}",
            "commit_sha": commit_sha,
            "targets": targets,
            "accepted_by_profile": {k: len(v) for k, v in rows_by_profile.items()},
            "candidate_rows": total_candidates,
            "filtered_out": int(stats.get("filtered_out", 0)),
            "duplicate_source_id": int(stats.get("duplicate_source_id", 0)),
        }
        summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        print(
            json.dumps(
                {
                    "status": "ok",
                    "profile": "all_modern",
                    "repo": f"{args.owner}/{args.repo}",
                    "commit_sha": commit_sha,
                    "accepted": len(all_rows),
                    "candidate_rows": total_candidates,
                    "filtered_out": rejected_count,
                    "target": sum(targets.values()),
                    "summary": str(summary_path),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.profile == "classical_restraint":
        output_default = f"corpus/_clean/poetry_classical_{args.profile}.github.json"
    else:
        output_default = f"corpus/_clean/lyrics_modern_zh_{args.profile}.github.json"
    proof_default = f"corpus/_clean/_github_{args.profile}_proof.json"
    output_path = (repo_root / (args.output or output_default)).resolve()
    proof_path = (repo_root / (args.proof or proof_default)).resolve()

    if args.profile == "classical_restraint":
        rows, rejected_count, total_candidates = _build_classical_rows_with_stats(
            raw_repo,
            owner=args.owner,
            repo=args.repo,
            target_count=args.target_count,
        )
    else:
        rows_by_profile, stats = build_modern_disjoint_rows_from_raw(
            raw_repo,
            owner=args.owner,
            repo=args.repo,
            targets={
                "uplift_pop": args.target_count if args.profile == "uplift_pop" else 0,
                "urban_introspective": args.target_count if args.profile == "urban_introspective" else 0,
                "club_dance": args.target_count if args.profile == "club_dance" else 0,
                "ambient_meditation": args.target_count if args.profile == "ambient_meditation" else 0,
            },
        )
        rows = list(rows_by_profile.get(args.profile, []))
        total_candidates = int(stats.get("candidate_rows", 0))
        rejected_count = int(stats.get("filtered_out", 0)) + int(stats.get("duplicate_source_id", 0))

    _write_rows(output_path, rows)
    if args.merge_into_main:
        if args.profile == "uplift_pop":
            _replace_uplift_rows(repo_root / "corpus/lyrics_modern_zh.json", rows)
        elif args.profile == "urban_introspective":
            _replace_urban_rows(repo_root / "corpus/lyrics_modern_zh.json", rows)
        elif args.profile == "club_dance":
            _replace_club_rows(repo_root / "corpus/lyrics_modern_zh.json", rows)
        elif args.profile == "ambient_meditation":
            _replace_ambient_rows(repo_root / "corpus/lyrics_modern_zh.json", rows)
        else:
            _replace_classical_rows(repo_root / "corpus/poetry_classical.json", rows)

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
                "profile": args.profile,
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


def _replace_urban_rows(main_corpus_path: Path, urban_rows: list[dict[str, Any]]) -> None:
    if main_corpus_path.exists():
        data = json.loads(main_corpus_path.read_text(encoding="utf-8"))
        existing = [row for row in data if isinstance(row, dict)]
    else:
        existing = []

    kept = [row for row in existing if str(row.get("profile_tag", "")).strip() != "urban_introspective"]
    merged = kept + urban_rows
    _write_rows(main_corpus_path, merged)


def _replace_club_rows(main_corpus_path: Path, club_rows: list[dict[str, Any]]) -> None:
    if main_corpus_path.exists():
        data = json.loads(main_corpus_path.read_text(encoding="utf-8"))
        existing = [row for row in data if isinstance(row, dict)]
    else:
        existing = []

    kept = [row for row in existing if str(row.get("profile_tag", "")).strip() != "club_dance"]
    merged = kept + club_rows
    _write_rows(main_corpus_path, merged)


def _replace_ambient_rows(main_corpus_path: Path, ambient_rows: list[dict[str, Any]]) -> None:
    if main_corpus_path.exists():
        data = json.loads(main_corpus_path.read_text(encoding="utf-8"))
        existing = [row for row in data if isinstance(row, dict)]
    else:
        existing = []

    kept = [row for row in existing if str(row.get("profile_tag", "")).strip() != "ambient_meditation"]
    merged = kept + ambient_rows
    _write_rows(main_corpus_path, merged)


def _replace_all_modern_rows(main_corpus_path: Path, rows_by_profile: dict[str, list[dict[str, Any]]]) -> None:
    if main_corpus_path.exists():
        data = json.loads(main_corpus_path.read_text(encoding="utf-8"))
        existing = [row for row in data if isinstance(row, dict)]
    else:
        existing = []

    modern_profiles = {"uplift_pop", "urban_introspective", "club_dance", "ambient_meditation"}
    kept = [row for row in existing if str(row.get("profile_tag", "")).strip() not in modern_profiles]
    merged = list(kept)
    for profile in ["uplift_pop", "urban_introspective", "club_dance", "ambient_meditation"]:
        merged.extend(list(rows_by_profile.get(profile, [])))
    _write_rows(main_corpus_path, merged)


def _write_modern_outputs_and_proofs(
    *,
    repo_root: Path,
    owner: str,
    repo: str,
    commit_sha: str,
    rows_by_profile: dict[str, list[dict[str, Any]]],
    rejected_count: int,
) -> None:
    for profile in ["uplift_pop", "urban_introspective", "club_dance", "ambient_meditation"]:
        rows = list(rows_by_profile.get(profile, []))
        output_path = repo_root / f"corpus/_clean/lyrics_modern_zh_{profile}.github.json"
        proof_path = repo_root / f"corpus/_clean/_github_{profile}_proof.json"
        _write_rows(output_path, rows)
        write_proof_file(
            proof_path=proof_path,
            owner=owner,
            repo=repo,
            commit_sha=commit_sha,
            rows=rows,
            rejected_count=rejected_count,
        )


if __name__ == "__main__":
    raise SystemExit(main())
