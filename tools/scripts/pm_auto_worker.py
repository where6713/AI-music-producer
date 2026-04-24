from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


TASK_RE = re.compile(r"\[(PM-AUTO-TASK-[0-9]+|TASK-[A-Z0-9-]+)\]")
AUTO_RUN_RE = re.compile(r"^AUTO_RUN:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


@dataclass
class TaskComment:
    comment_id: str
    task_tag: str
    body: str
    auto_run: str


def parse_task_comment(comment_id: str, body: str) -> TaskComment | None:
    hit = TASK_RE.search(body)
    if not hit:
        return None
    cmd_hit = AUTO_RUN_RE.search(body)
    return TaskComment(
        comment_id=comment_id.strip(),
        task_tag=hit.group(1),
        body=body,
        auto_run=(cmd_hit.group(1).strip() if cmd_hit else ""),
    )


def _run(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _tail(text: str, max_chars: int = 700) -> str:
    val = (text or "").strip()
    if len(val) <= max_chars:
        return val
    return val[-max_chars:]


def gh_pr_comment(pr_number: int, body: str) -> None:
    _run(["gh", "pr", "comment", str(pr_number), "--body", body], timeout=120)


def fetch_latest_comment(repo: str, pr_number: int) -> tuple[str, str] | None:
    proc = _run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{pr_number}/comments?per_page=1",
        ],
        timeout=120,
    )
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    last = payload[-1]
    if not isinstance(last, dict):
        return None
    return str(last.get("id", "")).strip(), str(last.get("body", ""))


def process_one(repo: str, pr_number: int, state_path: Path, log_path: Path) -> bool:
    latest = fetch_latest_comment(repo, pr_number)
    if not latest:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("latest comment fetch failed\n", encoding="utf-8")
        return False

    comment_id, body = latest
    task = parse_task_comment(comment_id, body)
    if not task:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("heartbeat: no task tag\n")
        return False

    last_id = state_path.read_text(encoding="utf-8").strip() if state_path.exists() else ""
    if task.comment_id == last_id:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"heartbeat: already processed {task.task_tag}\n")
        return False

    gh_pr_comment(pr_number, f"ACK {task.task_tag}, START NOW, ETA 30m")

    if not task.auto_run:
        gh_pr_comment(
            pr_number,
            f"BLOCKED {task.task_tag} + missing AUTO_RUN directive + need executable command input",
        )
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(task.comment_id, encoding="utf-8")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"blocked: {task.task_tag} missing AUTO_RUN\n")
        return True

    run_proc = _run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", task.auto_run], timeout=1800)
    stdout_tail = _tail(run_proc.stdout)
    stderr_tail = _tail(run_proc.stderr)
    if run_proc.returncode == 0:
        gh_pr_comment(
            pr_number,
            "\n".join(
                [
                    f"DONE {task.task_tag} + command completed",
                    f"evidence command: {task.auto_run}",
                    f"stdout tail: {stdout_tail}",
                ]
            ),
        )
    else:
        gh_pr_comment(
            pr_number,
            "\n".join(
                [
                    f"BLOCKED {task.task_tag} + command failed + need corrected AUTO_RUN",
                    f"evidence command: {task.auto_run}",
                    f"stderr tail: {stderr_tail}",
                ]
            ),
        )

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(task.comment_id, encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"processed: {task.task_tag}, rc={run_proc.returncode}\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="PM auto task worker")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--state", default=".tmp/pm_worker.state")
    parser.add_argument("--log", default=".tmp/pm_worker.log")
    parser.add_argument("--interval", default=20, type=int)
    parser.add_argument("--lock", default=".tmp/pm_worker.lock")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state_path = Path(args.state)
    log_path = Path(args.log)
    lock_path = Path(args.lock)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not state_path.exists():
        state_path.write_text("", encoding="utf-8")

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("lock-exists: another worker is already running\n")
        return 2

    os.write(fd, str(os.getpid()).encode("utf-8"))
    os.close(fd)

    def _cleanup_lock() -> None:
        try:
            if lock_path.exists():
                lock_path.unlink()
        except Exception:
            pass

    atexit.register(_cleanup_lock)

    if args.once:
        process_one(args.repo, args.pr, state_path, log_path)
        return 0

    while True:
        try:
            process_one(args.repo, args.pr, state_path, log_path)
        except Exception as exc:  # pragma: no cover
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"error: {exc}\n")
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
