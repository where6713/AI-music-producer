from __future__ import annotations

import subprocess
import sys


def _read_local_hooks_path() -> str | None:
    result = subprocess.run(
        ["git", "config", "--local", "--get", "core.hooksPath"],
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.decode("utf-8", errors="replace").strip()
    return value or None


def _restore_local_hooks_path(original: str | None) -> None:
    if original is None:
        subprocess.run(
            ["git", "config", "--local", "--unset", "core.hooksPath"],
            capture_output=True,
            text=False,
            check=False,
        )
        return

    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", original],
        capture_output=True,
        text=False,
        check=False,
    )


def test_cli_status() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "status"],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "ready" in stdout.lower()


def test_cli_docs_alignment_check_reports_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "docs-alignment-check",
            "docs/映月工厂_极简歌词工坊_PRD.json",
            "one law.md",
            "目录框架规范.md",
            "docs/ai_doc_manifest.json",
            "out/lyrics.txt",
            "out/style.txt",
            "out/exclude.txt",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G4 DOCS-ALIGNMENT PASS" in stdout


def test_cli_self_check_g0_reports_pass() -> None:
    original = _read_local_hooks_path()
    try:
        set_result = subprocess.run(
            ["git", "config", "--local", "core.hooksPath", "tools/githooks"],
            capture_output=True,
            text=False,
            check=False,
        )
        assert set_result.returncode == 0

        result = subprocess.run(
            [sys.executable, "-m", "apps.cli.main", "self-check", "g0"],
            capture_output=True,
            text=False,
            check=False,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        assert result.returncode == 0
        assert "G0 PASS" in stdout
    finally:
        _restore_local_hooks_path(original)


def test_cli_scope_check_g1_reports_pass() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "scope-check", "g1"],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert "G1 SCOPE-CHECK" in stdout


def test_cli_failure_evidence_check_requires_failure_output() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "failure-evidence-check",
            "symptom",
            "trigger",
            "root",
            "command",
            "failure output snapshot",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G2 FAILURE-EVIDENCE PASS" in stdout


def test_cli_pass_evidence_check_requires_outputs() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "pass-evidence-check",
            "pytest -q",
            "pass",
            "success",
            "https://github.com/where6713/AI-music-producer/actions/runs/1",
            "pytest -q",
            "python -m apps.cli.main gate-check --all",
            "25 passed",
            "ci-quality-gates: success",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G3 PASS-EVIDENCE PASS" in stdout
