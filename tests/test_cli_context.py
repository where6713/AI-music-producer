import subprocess
import sys


def test_cli_context_command_outputs_summary() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "context"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip()
    # Fresh repo state may have no notepad context yet.
    assert (
        "LEARNINGS" in result.stdout
        or "No project memory context available." in result.stdout
    )
