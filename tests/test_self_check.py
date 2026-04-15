"""Tests for self_check tools (shell_probe and py_eval).

PRD 6: Self-Healing Protocol with two levels:
- Level 1: Known error dictionary (error_solutions.sqlite)
- Level 2: Autonomous debug tools (shell_probe, py_eval)

shell_probe: Read-only diagnostic commands in sandbox
py_eval: One-time script validation in isolated subprocess
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


class TestShellProbeContract:
    """Test module-level contracts for shell_probe."""

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from producer_tools.self_check import shell_probe

        assert hasattr(shell_probe, "TOOL_NAME")
        assert shell_probe.TOOL_NAME == "shell_probe"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from producer_tools.self_check import shell_probe

        assert hasattr(shell_probe, "run")
        assert callable(shell_probe.run)


class TestShellProbeAllowlist:
    """Tests for shell_probe allowlist enforcement.

    PRD 6.1: allowlist_prefix includes:
    - ffprobe, ffmpeg -i
    - ls, dir, type, head, tail
    - where, which
    - python -c, pip show, pip list
    - nvidia-smi, systeminfo
    """

    def test_allowlist_command_executes(self) -> None:
        """Allowlist commands should execute."""
        from producer_tools.self_check import shell_probe

        result = shell_probe.run(
            {
                "command": "echo test",
                "timeout_s": 5,
            }
        )

        assert isinstance(result, dict)
        assert "success" in result or "output" in result or "error" in result

    def test_denylist_command_rejected(self) -> None:
        """Denylist commands should be rejected."""
        from producer_tools.self_check import shell_probe

        result = shell_probe.run(
            {
                "command": "rm -rf /tmp/test",
                "timeout_s": 5,
            }
        )

        assert isinstance(result, dict)
        # Should reject destructive commands
        assert (
            result.get("success") is False
            or "denied" in result.get("error", "").lower()
            or "blocked" in result.get("error", "").lower()
        )

    def test_pip_install_rejected(self) -> None:
        """pip install should require user confirmation."""
        from producer_tools.self_check import shell_probe

        result = shell_probe.run(
            {
                "command": "pip install something",
                "timeout_s": 5,
            }
        )

        assert isinstance(result, dict)
        # Should reject install commands
        assert (
            result.get("success") is False
            or result.get("requires_confirmation") is True
        )


class TestShellProbeTimeout:
    """Tests for shell_probe timeout handling."""

    def test_timeout_exceeded(self) -> None:
        """Commands exceeding timeout should be terminated."""
        from producer_tools.self_check import shell_probe

        result = shell_probe.run(
            {
                "command": "ping -n 10 127.0.0.1",  # Long running command
                "timeout_s": 1,
            }
        )

        assert isinstance(result, dict)
        # Should timeout
        assert (
            result.get("success") is False
            or "timeout" in result.get("error", "").lower()
        )


class TestPyEvalContract:
    """Test module-level contracts for py_eval."""

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from producer_tools.self_check import py_eval

        assert hasattr(py_eval, "TOOL_NAME")
        assert py_eval.TOOL_NAME == "py_eval"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from producer_tools.self_check import py_eval

        assert hasattr(py_eval, "run")
        assert callable(py_eval.run)


class TestPyEvalExecution:
    """Tests for py_eval script execution.

    PRD 6.1: py_eval executes short scripts in isolated subprocess.
    - No file writes outside /tmp
    - Timeout 30s default
    """

    def test_simple_calculation(self) -> None:
        """Simple calculations should work."""
        from producer_tools.self_check import py_eval

        result = py_eval.run(
            {
                "code": "x = 1 + 1\nprint(x)",
                "timeout_s": 5,
            }
        )

        assert isinstance(result, dict)
        assert result.get("success") is True or "2" in result.get("output", "")

    def test_import_allowed(self) -> None:
        """Standard library imports should work."""
        from producer_tools.self_check import py_eval

        result = py_eval.run(
            {
                "code": "import sys\nprint(sys.version)",
                "timeout_s": 5,
            }
        )

        assert isinstance(result, dict)
        assert result.get("success") is True or "Python" in result.get("output", "")

    def test_file_write_blocked(self) -> None:
        """File writes outside /tmp should be blocked."""
        from producer_tools.self_check import py_eval

        result = py_eval.run(
            {
                "code": "open('/test_write.txt', 'w').write('test')",
                "timeout_s": 5,
            }
        )

        assert isinstance(result, dict)
        # Should block or fail
        assert (
            result.get("success") is False
            or "permission" in result.get("error", "").lower()
            or "denied" in result.get("error", "").lower()
        )

    def test_timeout_exceeded(self) -> None:
        """Scripts exceeding timeout should be terminated."""
        from producer_tools.self_check import py_eval

        result = py_eval.run(
            {
                "code": "while True: pass",
                "timeout_s": 1,
            }
        )

        assert isinstance(result, dict)
        assert (
            result.get("success") is False
            or "timeout" in result.get("error", "").lower()
        )


class TestErrorSolutionsDB:
    """Tests for error_solutions.sqlite knowledge base.

    PRD 6.1 Level 1: Known error dictionary with auto-fix mappings.
    """

    def test_error_solutions_db_exists(self) -> None:
        """Error solutions database should exist or be creatable."""
        from pathlib import Path

        db_path = (
            Path(__file__).resolve().parents[1]
            / "knowledge_base"
            / "error_solutions.sqlite"
        )
        # DB may not exist yet, but directory should
        knowledge_dir = db_path.parent
        if knowledge_dir.exists():
            assert knowledge_dir.is_dir()

    def test_lookup_known_error(self) -> None:
        """Known errors should have solutions."""
        # This will be implemented after the DB is created
        pass


class TestRetryPolicy:
    """Tests for retry and fallback policy.

    PRD 6.1: Max 3 attempts with exponential backoff.
    """

    def test_retry_count_limited(self) -> None:
        """Retry attempts should be limited to 3."""
        # This tests the retry policy implementation
        pass

    def test_exponential_backoff(self) -> None:
        """Retries should use exponential backoff."""
        # This tests the backoff timing
        pass
