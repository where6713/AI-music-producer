from __future__ import annotations

import subprocess
import sys


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
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "self-check", "g0"],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G0 PASS" in stdout


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
