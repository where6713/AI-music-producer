"""Shell probe tool for diagnostic commands in sandbox.

PRD 6.1 Level 2: Autonomous debug tools.
- Read-only diagnostic commands
- Allowlist/denylist enforcement
- Timeout handling
- User confirmation for install/write commands
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ..contracts import ToolPayload, ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "shell_probe"

logger = logging.getLogger(__name__)

# PRD 6.1: Allowlist prefixes - read-only diagnostic commands
ALLOWLIST_PREFIXES: tuple[str, ...] = (
    "ffprobe",
    "ffmpeg -i",
    "ls",
    "dir",
    "type",
    "head",
    "tail",
    "where",
    "which",
    "python -c",
    "pip show",
    "pip list",
    "nvidia-smi",
    "systeminfo",
    "echo",
    "cat",
    "pwd",
    "cd",  # For navigation, but read-only
    "Get-",
    "Write-Output",
    "Write-Host",
)

# PRD 6.1: Denylist prefixes - destructive/install commands
DENYLIST_PREFIXES: tuple[str, ...] = (
    "rm",
    "del",
    "rmdir",
    "format",
    "mkfs",
    "shutdown",
    "reboot",
    "pip install",
    "pip uninstall",
    "curl",
    "wget",
    "Invoke-WebRequest",
    "Remove-Item",
    "Delete",
    "Format-",
    "New-Item",  # May create files
    "Set-Content",  # Writes to files
    "Out-File",
    ">",
    ">>",
)

# Commands that require user confirmation before execution
REQUIRES_CONFIRMATION_PREFIXES: tuple[str, ...] = (
    "pip install",
    "pip uninstall",
    "pip download",
    "conda install",
    "choco install",
    "winget install",
    "apt install",
    "brew install",
)

DEFAULT_TIMEOUT_S = 30


def _check_allowlist(command: str) -> bool:
    """Check if command matches allowlist.

    Args:
        command: Command string to check

    Returns:
        True if command is allowed (matches allowlist)
    """
    cmd_lower = command.lower().strip()

    # First check denylist - denylist takes priority
    for prefix in DENYLIST_PREFIXES:
        if prefix.lower() in cmd_lower:
            return False

    # Then check allowlist
    for prefix in ALLOWLIST_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            return True

    # Default: unknown commands are not allowed
    return False


def _requires_confirmation(command: str) -> bool:
    """Check if command requires user confirmation.

    Args:
        command: Command string to check

    Returns:
        True if command needs user approval
    """
    cmd_lower = command.lower().strip()

    for prefix in REQUIRES_CONFIRMATION_PREFIXES:
        if cmd_lower.startswith(prefix.lower()):
            return True

    return False


def _is_denylisted(command: str) -> bool:
    """Check if command is explicitly denied.

    Args:
        command: Command string to check

    Returns:
        True if command is on denylist
    """
    cmd_lower = command.lower().strip()

    for prefix in DENYLIST_PREFIXES:
        if prefix.lower() in cmd_lower:
            return True

    return False


def run(payload: ToolPayload) -> ToolResult:
    """Execute the shell_probe tool.

    PRD 6.1: Runs read-only diagnostic commands in sandbox.

    Args:
        payload: Must contain:
            - command: Shell command to execute

        Optional:
            - timeout_s: Timeout in seconds (default 30)

    Returns:
        ToolResult containing:
            - success: bool
            - output: Command stdout/stderr
            - error: Error message if failed
            - requires_confirmation: bool if command needs user approval

    Raises:
        ValueError: If command is missing
    """
    command = payload.get("command")
    if not command:
        raise ValueError("command is required")

    if not isinstance(command, str):
        raise ValueError("command must be a string")

    timeout_s = payload.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not isinstance(timeout_s, (int, float)):
        timeout_s = DEFAULT_TIMEOUT_S

    # Check if command requires user confirmation
    if _requires_confirmation(command):
        return {
            "success": False,
            "error": f"Command '{command}' requires user confirmation before execution. Please ask the user for approval.",
            "requires_confirmation": True,
            "command": command,
        }

    # Check if command is denylisted
    if _is_denylisted(command):
        return {
            "success": False,
            "error": f"Command '{command}' is blocked. Destructive/install commands are not allowed in shell_probe.",
            "blocked": True,
            "command": command,
        }

    # Check if command is allowed
    if not _check_allowlist(command):
        return {
            "success": False,
            "error": f"Command '{command}' is not in the allowlist. Only read-only diagnostic commands are permitted.",
            "blocked": True,
            "command": command,
        }

    # Execute the command
    try:
        # Use shell=True for Windows command execution
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=True,
        )

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        return {
            "success": result.returncode == 0,
            "output": output.strip(),
            "return_code": result.returncode,
            "command": command,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout_s} seconds",
            "timeout": True,
            "command": command,
        }
    except Exception as e:
        logger.exception("shell_probe execution failed")
        return {
            "success": False,
            "error": str(e),
            "command": command,
        }
