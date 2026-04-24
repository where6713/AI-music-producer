from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import subprocess
import os


_COMMIT_SUBJECT_RE = re.compile(
    r"^(feat|fix|docs|refactor|test|chore|build|ci|perf|revert)\([a-z0-9._/-]+\): .+"
)
_GATE_SCOPE_RE = re.compile(r"\((g[1-7])\)", re.IGNORECASE)


def validate_g1_scope(payload: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []

    subject_raw = payload.get("commit_subject", "")
    commit_subject = subject_raw if isinstance(subject_raw, str) else ""
    changed_raw = payload.get("changed_files", [])
    changed_files = (
        [x for x in changed_raw if isinstance(x, str) and x.strip()]
        if isinstance(changed_raw, list)
        else []
    )

    if not commit_subject or not _COMMIT_SUBJECT_RE.match(commit_subject):
        failed_checks.append("commit_message_format")

    docs_only_commit = bool(changed_files) and all(path.startswith("docs/") for path in changed_files)

    if not _GATE_SCOPE_RE.search(commit_subject) and not docs_only_commit:
        failed_checks.append("commit_scope_gate")

    if not changed_files:
        failed_checks.append("changed_files_present")

    has_gitkeep = any(path.endswith(".gitkeep") for path in changed_files)
    if has_gitkeep and len(changed_files) > 1:
        failed_checks.append("mixed_gitkeep_cleanup")

    return {
        "status": "pass" if not failed_checks else "fail",
        "failed_checks": failed_checks,
        "commit_subject": commit_subject,
        "changed_files": changed_files,
    }


def _read_git_output(workspace_root: Path, args: list[str]) -> str:
    raw = subprocess.check_output(
        ["git", *args],
        cwd=str(workspace_root),
        stderr=subprocess.DEVNULL,
        text=False,
    )
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def check_gate_g1(workspace_root: Path, target_commit: str = "") -> dict[str, Any]:
    explicit_target = str(target_commit or os.getenv("G1_TARGET_SHA", "")).strip()
    if explicit_target:
        try:
            explicit_subject = _read_git_output(
                workspace_root,
                ["show", "-s", "--format=%s", explicit_target],
            ).strip()
            explicit_changed = _read_git_output(
                workspace_root,
                ["show", "--name-only", "--pretty=", explicit_target],
            )
            explicit_files = [line.strip() for line in explicit_changed.splitlines() if line.strip()]
            return validate_g1_scope(
                {"commit_subject": explicit_subject, "changed_files": explicit_files}
            )
        except Exception:
            return {
                "status": "fail",
                "failed_checks": ["target_commit_unavailable"],
                "commit_subject": "",
                "changed_files": [],
            }

    try:
        commit_subject = _read_git_output(workspace_root, ["log", "-1", "--pretty=%s"]).strip()
        changed_output = _read_git_output(
            workspace_root,
            ["show", "--name-only", "--pretty=", "-1"],
        )
    except Exception:
        return {
            "status": "fail",
            "failed_checks": ["git_metadata_unavailable"],
            "commit_subject": "",
            "changed_files": [],
        }

    changed_files = [line.strip() for line in changed_output.splitlines() if line.strip()]
    primary = validate_g1_scope(
        {"commit_subject": commit_subject, "changed_files": changed_files}
    )

    is_merge_head = commit_subject.lower().startswith("merge ")
    if primary["status"] == "pass" or not is_merge_head:
        return primary

    try:
        pr_head_subject = _read_git_output(
            workspace_root,
            ["show", "-s", "--format=%s", "HEAD^2"],
        ).strip()
        pr_head_changed = _read_git_output(
            workspace_root,
            ["show", "--name-only", "--pretty=", "HEAD^2"],
        )
        pr_head_files = [line.strip() for line in pr_head_changed.splitlines() if line.strip()]
        pr_head_result = validate_g1_scope(
            {"commit_subject": pr_head_subject, "changed_files": pr_head_files}
        )
        if pr_head_result["status"] == "pass":
            return pr_head_result
    except Exception:
        pass

    try:
        non_merge_sha = _read_git_output(
            workspace_root,
            ["rev-list", "--no-merges", "-n", "1", "HEAD"],
        ).strip()
        if not non_merge_sha:
            return primary
        fallback_subject = _read_git_output(
            workspace_root,
            ["show", "-s", "--format=%s", non_merge_sha],
        ).strip()
        fallback_changed = _read_git_output(
            workspace_root,
            ["show", "--name-only", "--pretty=", non_merge_sha],
        )
    except Exception:
        return primary

    fallback_files = [line.strip() for line in fallback_changed.splitlines() if line.strip()]
    return validate_g1_scope(
        {"commit_subject": fallback_subject, "changed_files": fallback_files}
    )
