"""Terminal UX tools for AI-music-producer.

PRD 8: User experience
- 8.1 Terminal playback (sounddevice + soundfile)
- 8.2 Auto-import from watchdog downloads
- 8.3 Rich streaming output

PRD 9: CLI command routing - natural language first
"""

from __future__ import annotations

from .audio_player import TOOL_NAME as AUDIO_PLAYER_NAME
from .audio_player import run as play_audio
from .cli_router import run as route_command
from .cli_router import TOOL_NAME as CLI_ROUTER_NAME
from .download_watcher import run as watch_downloads
from .download_watcher import TOOL_NAME as DOWNLOAD_WATCHER_NAME
from .project_memory import run as manage_memory
from .project_memory import TOOL_NAME as PROJECT_MEMORY_NAME

__all__ = [
    "AUDIO_PLAYER_NAME",
    "AUDIO_PLAYER_TOOL_NAME",
    "CLI_ROUTER_NAME",
    "DOWNLOAD_WATCHER_NAME",
    "PROJECT_MEMORY_NAME",
    "play_audio",
    "route_command",
    "watch_downloads",
    "manage_memory",
]
