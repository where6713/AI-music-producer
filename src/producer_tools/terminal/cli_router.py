"""CLI router tool for natural language command routing.

PRD 9: CLI command routing - natural language first.

Routes commands to appropriate tools:
- play -> audio_player
- analyze -> style_deconstructor
- check-fit -> friction_calculator
- write-lyrics -> lyric_architect
- compile -> prompt_compiler
- master -> post_processor
- branch -> git checkout -b
- switch -> git checkout
- compare -> rich table diff
- status -> project status
- clean -> cleanup wizard
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from ..contracts import ToolPayload, ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "cli_router"

logger = logging.getLogger(__name__)

# Command patterns -> tool mapping
COMMAND_PATTERNS: dict[str, tuple[str, str]] = {
    # Tool commands
    r"^play(?:\s+(.+))?$": ("audio_player", "Play audio file"),
    r"^analyze(?:\s+(.+))?$": ("style_deconstructor", "Analyze reference audio"),
    r"^check-?fit(?:\s+(.+))?$": ("friction_calculator", "Check compatibility"),
    r"^write-?lyrics(?:\s+(.+))?$": ("lyric_architect", "Write lyrics"),
    r"^compile(?:\s+.*)?$": ("prompt_compiler", "Compile prompt"),
    r"^master(?:\s+(.+))?$": ("post_processor", "Master audio"),
    r"^use-?voice(?:\s+(.+))?$": ("acoustic_analyst", "Use voice profile"),
    # Git commands
    r"^branch(?:\s+(.+))?$": ("git_branch", "Create new branch"),
    r"^switch(?:\s+(.+))?$": ("git_switch", "Switch branch"),
    r"^compare(?:\s+(.+))?$": ("git_diff", "Compare branches"),
    # Project commands
    r"^status(?:\s*)$": ("project_status", "Show project status"),
    r"^clean(?:\s*)$": ("cleanup", "Cleanup wizard"),
    r"^new(?:\s+(.+))?$": ("project_new", "Create new project"),
}


def _route_to_tool(command: str, project_dir: Path) -> dict[str, object]:
    """Route command to appropriate tool.

    Args:
        command: Command string
        project_dir: Project directory

    Returns:
        dict with routing result
    """
    command_lower = command.lower().strip()

    for pattern, (tool, description) in COMMAND_PATTERNS.items():
        match = re.match(pattern, command_lower)
        if match:
            args = match.group(1).strip() if match.group(1) else None

            return {
                "tool": tool,
                "description": description,
                "args": args,
                "routed": True,
            }

    # Default: treat as natural language, return unhandled
    return {
        "tool": None,
        "routed": False,
        "message": "Command not recognized, treating as natural language",
        "command": command,
    }


def _handle_git_branch(branch_name: str | None, project_dir: Path) -> dict[str, object]:
    """Handle git branch creation.

    Args:
        branch_name: Name for new branch
        project_dir: Project directory

    Returns:
        dict with result
    """
    if not branch_name:
        return {
            "success": False,
            "error": "Branch name required. Usage: branch <semantic_name>",
        }

    try:
        # Create semantic branch name
        safe_name = re.sub(r"[^\w\-]", "_", branch_name.lower())
        result = subprocess.run(
            ["git", "checkout", "-b", safe_name],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "branch": safe_name,
                "message": f"Created and switched to branch '{safe_name}'",
            }
        else:
            return {
                "success": False,
                "error": result.stderr.strip(),
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def _handle_git_switch(target: str | None, project_dir: Path) -> dict[str, object]:
    """Handle git branch switching.

    Args:
        target: Branch name or number
        project_dir: Project directory

    Returns:
        dict with result
    """
    if not target:
        return {
            "success": False,
            "error": "Target required. Usage: switch <branch_name_or_number>",
        }

    try:
        result = subprocess.run(
            ["git", "checkout", target],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return {
                "success": True,
                "target": target,
                "message": f"Switched to '{target}'",
            }
        else:
            return {
                "success": False,
                "error": result.stderr.strip(),
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def run(payload: ToolPayload) -> ToolResult:
    """Execute the cli_router tool.

    PRD 9: Route commands to appropriate tools.

    Args:
        payload: Must contain:
            - command: Command string to route

        Optional:
            - project_dir: Project directory (default: current directory)

    Returns:
        ToolResult containing:
            - tool: Tool name to invoke
            - args: Arguments for the tool
            - routed: Whether command was successfully routed
    """
    command = payload.get("command")
    if not command:
        raise ValueError("command is required")
    if not isinstance(command, str):
        raise ValueError("command must be a string")

    project_dir = payload.get("project_dir")
    if project_dir and isinstance(project_dir, str):
        project_path = Path(project_dir)
    else:
        project_path = Path.cwd()

    # Route command
    routing_result = _route_to_tool(command, project_path)

    if not routing_result.get("routed"):
        return routing_result

    tool = routing_result.get("tool")
    args_raw = routing_result.get("args")
    args: str | None = args_raw if isinstance(args_raw, str) else None

    # Handle special cases
    if tool == "git_branch":
        return _handle_git_branch(args, project_path)
    elif tool == "git_switch":
        return _handle_git_switch(args, project_path)
    elif tool == "git_diff":
        return {
            "success": True,
            "tool": "git",
            "args": ["diff"],
            "message": "Run git diff in project directory",
        }
    elif tool == "project_status":
        return {
            "success": True,
            "tool": "status",
            "message": "Show project status",
        }
    elif tool == "cleanup":
        return {
            "success": True,
            "tool": "cleanup",
            "message": "Cleanup wizard",
        }
    elif tool == "project_new":
        return {
            "success": True,
            "tool": "new",
            "args": args,
            "message": "Create new project",
        }

    # Return tool routing result for other tools
    return routing_result
