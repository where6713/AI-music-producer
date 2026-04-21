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
