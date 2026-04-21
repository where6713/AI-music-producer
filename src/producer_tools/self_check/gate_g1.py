from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import subprocess


_COMMIT_SUBJECT_RE = re.compile(
    r"^(feat|fix|docs|refactor|test|chore|build|ci|perf|revert)\([a-z0-9._/-]+\): .+"
)


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

    if "(g1)" not in commit_subject.lower():
        failed_checks.append("commit_scope_g1")

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
    return subprocess.check_output(
        ["git", *args],
        cwd=str(workspace_root),
        stderr=subprocess.DEVNULL,
        text=True,
    )


def check_gate_g1(workspace_root: Path) -> dict[str, Any]:
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
    return validate_g1_scope(
        {"commit_subject": commit_subject, "changed_files": changed_files}
    )
