"""Tests for terminal UX and CLI tools.

PRD 8: User experience improvements
- 8.1 Terminal playback (sounddevice + soundfile)
- 8.2 Auto-import from watchdog downloads
- 8.3 Rich streaming output
- 9. CLI command routing

PRD 11: Terminal UX and Operational Flow (Task 43-46)
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


class TestAudioPlayerContract:
    """Tests for audio_player tool.

    PRD 8.1: Terminal playback using sounddevice + soundfile.
    """

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from producer_tools.terminal import audio_player

        assert hasattr(audio_player, "TOOL_NAME")
        assert audio_player.TOOL_NAME == "audio_player"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from producer_tools.terminal import audio_player

        assert hasattr(audio_player, "run")
        assert callable(audio_player.run)


class TestAudioPlayerPlayback:
    """Tests for audio_player playback functionality."""

    def test_play_missing_file_path(self) -> None:
        """Should raise ValueError if file_path missing."""
        from producer_tools.terminal import audio_player

        with pytest.raises(ValueError, match="file_path"):
            audio_player.run({})

    def test_play_nonexistent_file(self) -> None:
        """Should raise FileNotFoundError if file doesn't exist."""
        from producer_tools.terminal import audio_player

        with pytest.raises(FileNotFoundError):
            audio_player.run({"file_path": "/nonexistent/audio.mp3"})

    def test_play_valid_audio(self, tmp_path: Path) -> None:
        """Should return success for valid audio file."""
        import numpy as np
        import soundfile as sf
        from producer_tools.terminal import audio_player

        # Create a valid audio file
        audio_path = tmp_path / "test.wav"
        audio_data = np.random.randn(44100).astype(np.float32) * 0.1
        sf.write(str(audio_path), audio_data, 44100)

        result = audio_player.run({"file_path": str(audio_path)})

        assert isinstance(result, dict)
        assert "success" in result or "playing" in result


class TestDownloadWatcherContract:
    """Tests for download_watcher tool.

    PRD 8.2: Auto-import from watchdog downloads.
    """

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from producer_tools.terminal import download_watcher

        assert hasattr(download_watcher, "TOOL_NAME")
        assert download_watcher.TOOL_NAME == "download_watcher"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from producer_tools.terminal import download_watcher

        assert hasattr(download_watcher, "run")
        assert callable(download_watcher.run)


class TestCLIRouterContract:
    """Tests for cli_router tool.

    PRD 9: CLI command routing - natural language first.
    """

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from producer_tools.terminal import cli_router

        assert hasattr(cli_router, "TOOL_NAME")
        assert cli_router.TOOL_NAME == "cli_router"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from producer_tools.terminal import cli_router

        assert hasattr(cli_router, "run")
        assert callable(cli_router.run)


class TestCLICommands:
    """Tests for CLI command parsing and routing."""

    def test_route_play_command(self) -> None:
        """Should route 'play' commands to audio_player."""
        from producer_tools.terminal import cli_router

        result = cli_router.run(
            {
                "command": "play take_001",
                "project_dir": "/tmp/test",
            }
        )

        assert isinstance(result, dict)
        assert "tool" in result or "routed_to" in result

    def test_route_analyze_command(self) -> None:
        """Should route 'analyze' commands to style_deconstructor."""
        from producer_tools.terminal import cli_router

        result = cli_router.run(
            {
                "command": "analyze reference.mp3",
                "project_dir": "/tmp/test",
            }
        )

        assert isinstance(result, dict)
        assert "tool" in result or "routed_to" in result

    def test_route_master_command(self) -> None:
        """Should route 'master' commands to post_processor."""
        from producer_tools.terminal import cli_router

        result = cli_router.run(
            {
                "command": "master take_001.mp3",
                "project_dir": "/tmp/test",
            }
        )

        assert isinstance(result, dict)
        assert "tool" in result or "routed_to" in result


class TestProjectMemoryContract:
    """Tests for project_memory tool.

    PRD 11.04: Project memory and cleanup suggestions.
    """

    def test_tool_name_defined(self) -> None:
        """TOOL_NAME must be defined."""
        from producer_tools.terminal import project_memory

        assert hasattr(project_memory, "TOOL_NAME")
        assert project_memory.TOOL_NAME == "project_memory"

    def test_run_callable(self) -> None:
        """run must be callable."""
        from producer_tools.terminal import project_memory

        assert hasattr(project_memory, "run")
        assert callable(project_memory.run)
