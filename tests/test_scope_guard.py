"""Tests for scope guard and non-goals enforcement.

PRD 11: Non-Goals and Scope Guard
- Automated guardrails for explicit non-goals from PRD
- Dependency and feature drift checks
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


class TestNonGoalsGuardrails:
    """Tests for non-goals guardrails enforcement.

    PRD 11: These features should NOT be implemented.
    """

    def test_no_realtime_audio_streaming(self) -> None:
        """Real-time audio streaming should not be implemented."""
        from producer_tools import business, orchestrator, self_check, terminal

        # Check that no module has realtime/streaming audio monitoring
        import inspect

        for module in [business, self_check, terminal, orchestrator]:
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) or inspect.isclass(obj):
                    doc = inspect.getdoc(obj) or ""
                    source = inspect.getsource(obj) if inspect.isfunction(obj) else ""
                    # Should not mention realtime streaming
                    assert "realtime stream" not in doc.lower()
                    assert "realtime stream" not in source.lower()

    def test_no_multi_agent(self) -> None:
        """Multi-agent orchestration should not be implemented."""
        # Check that orchestrator is single-agent
        from producer_tools.orchestrator import orchestrator

        assert "multi_agent" not in orchestrator.__doc__ or orchestrator.__doc__ is None

    def test_no_web_ui(self) -> None:
        """Web/Desktop GUI should not be implemented."""
        # Check no GUI-related modules
        from producer_tools import terminal

        assert not hasattr(terminal, "web_server")
        assert not hasattr(terminal, "gui")
        assert not hasattr(terminal, "tui")

    def test_no_docker(self) -> None:
        """Docker/WSL should not be used."""
        # Check no docker-related code
        from producer_tools import orchestrator

        doc = orchestrator.__doc__ or ""
        assert "docker" not in doc.lower()
        assert "podman" not in doc.lower()
        assert "wsl" not in doc.lower()

    def test_no_blockchain(self) -> None:
        """Blockchain storage should not be implemented."""
        from producer_tools import orchestrator

        doc = orchestrator.__doc__ or ""
        assert "blockchain" not in doc.lower()


class TestDependencyChecks:
    """Tests for dependency and feature drift checks."""

    def test_all_business_tools_have_run(self) -> None:
        """All business tools should expose run function."""
        from producer_tools.business import (
            acoustic_analyst,
            friction_calculator,
            lyric_architect,
            post_processor,
            prompt_compiler,
            style_deconstructor,
        )

        for tool in [
            acoustic_analyst,
            friction_calculator,
            lyric_architect,
            post_processor,
            prompt_compiler,
            style_deconstructor,
        ]:
            assert hasattr(tool, "run")
            assert callable(tool.run)

    def test_all_self_check_tools_have_run(self) -> None:
        """All self-check tools should expose run function."""
        from producer_tools.self_check import py_eval, shell_probe

        for tool in [shell_probe, py_eval]:
            assert hasattr(tool, "run")
            assert callable(tool.run)

    def test_all_terminal_tools_have_run(self) -> None:
        """All terminal tools should expose run function."""
        from producer_tools.terminal import (
            audio_player,
            cli_router,
            download_watcher,
            project_memory,
        )

        for tool in [audio_player, cli_router, download_watcher, project_memory]:
            assert hasattr(tool, "run")
            assert callable(tool.run)

    def test_orchestrator_has_run(self) -> None:
        """Orchestrator should expose run function."""
        from producer_tools.orchestrator import orchestrator

        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)


class TestFeatureDrift:
    """Tests for feature drift detection."""

    def test_tool_names_consistent(self) -> None:
        """All tools should have consistent TOOL_NAME attributes."""
        from producer_tools.business import acoustic_analyst
        from producer_tools.self_check import py_eval, shell_probe
        from producer_tools.terminal import audio_player
        from producer_tools.orchestrator import orchestrator

        # All should have TOOL_NAME
        for tool in [
            acoustic_analyst,
            py_eval,
            shell_probe,
            audio_player,
            orchestrator,
        ]:
            assert hasattr(tool, "TOOL_NAME")
            assert isinstance(tool.TOOL_NAME, str)
            assert len(tool.TOOL_NAME) > 0
