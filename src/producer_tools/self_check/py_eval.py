"""Python eval tool for one-time script validation in isolated subprocess.

PRD 6.1 Level 2: Autonomous debug tools.
- Execute short Python scripts for hypothesis validation
- No file writes outside /tmp
- Timeout 30s default
- Isolated subprocess execution
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ..contracts import ToolPayload, ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "py_eval"

logger = logging.getLogger(__name__)

# Default timeout for script execution
DEFAULT_TIMEOUT_S = 30

# Forbidden patterns in code - prevent destructive operations
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "os.system",
    "os.popen",
    "subprocess.call",
    "subprocess.run",
    "subprocess.Popen",
    "shutil.rmtree",
    "shutil.copy",
    "shutil.move",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "__import__",
    "importlib",
    "ctypes",
    "multiprocessing",
    "threading",
)

# Allowed write paths (temp directories)
ALLOWED_WRITE_PREFIXES: tuple[str, ...] = (
    str(tempfile.gettempdir()),
    "/tmp",
)


def _check_code_safety(code: str) -> str | None:
    """Check if code contains forbidden patterns.

    Args:
        code: Python code to check

    Returns:
        None if safe, error message if forbidden pattern found
    """
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code:
            return f"Forbidden pattern '{pattern}' in code. System/subprocess calls are not allowed."
    return None


def _check_file_write_safety(code: str) -> str | None:
    """Check if code attempts file writes outside allowed paths.

    Args:
        code: Python code to check

    Returns:
        None if safe, error message if unsafe write detected
    """
    # Simple heuristic: check for open() with write modes outside /tmp
    if "open(" in code and (
        "'w'" in code or '"w"' in code or "'a'" in code or '"a"' in code
    ):
        # Check if any allowed write prefix is mentioned
        has_allowed_path = any(prefix in code for prefix in ALLOWED_WRITE_PREFIXES)
        if not has_allowed_path:
            return "File write operations are only allowed in temporary directories (/tmp)."
    return None


def run(payload: ToolPayload) -> ToolResult:
    """Execute the py_eval tool.

    PRD 6.1: Execute short Python scripts in isolated subprocess.
    No file writes outside /tmp, timeout 30s default.

    Args:
        payload: Must contain:
            - code: Python code string to execute

        Optional:
            - timeout_s: Timeout in seconds (default 30)

    Returns:
        ToolResult containing:
            - success: bool
            - output: Script stdout
            - error: Error message if failed
            - timeout: bool if timed out

    Raises:
        ValueError: If code is missing
    """
    code = payload.get("code")
    if not code:
        raise ValueError("code is required")

    if not isinstance(code, str):
        raise ValueError("code must be a string")

    timeout_s = payload.get("timeout_s", DEFAULT_TIMEOUT_S)
    if not isinstance(timeout_s, (int, float)):
        timeout_s = DEFAULT_TIMEOUT_S

    # Safety checks
    safety_error = _check_code_safety(code)
    if safety_error:
        return {
            "success": False,
            "error": safety_error,
            "code": code,
        }

    write_error = _check_file_write_safety(code)
    if write_error:
        return {
            "success": False,
            "error": write_error,
            "code": code,
        }

    # Execute code in isolated subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )

        output = result.stdout
        error_output = result.stderr

        return {
            "success": result.returncode == 0,
            "output": output.strip(),
            "error": error_output.strip() if error_output else None,
            "return_code": result.returncode,
            "code": code,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Script timed out after {timeout_s} seconds",
            "timeout": True,
            "code": code,
        }
    except Exception as e:
        logger.exception("py_eval execution failed")
        return {
            "success": False,
            "error": str(e),
            "code": code,
        }
