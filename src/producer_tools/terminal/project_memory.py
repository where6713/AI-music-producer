"""Project memory tool for state management.

PRD 11.04: Project memory and cleanup suggestions.

Features:
- Track project state
- Provide cleanup suggestions
- Manage project metadata
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..contracts import ToolPayload, ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "project_memory"

logger = logging.getLogger(__name__)

# Project metadata file
PROJECT_METADATA_FILE = ".project_metadata.json"


def _get_project_metadata(project_dir: Path) -> dict[str, object]:
    """Get or create project metadata.

    Args:
        project_dir: Project directory

    Returns:
        dict with project metadata
    """
    metadata_file = project_dir / PROJECT_METADATA_FILE

    if metadata_file.exists():
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Default metadata
    return {
        "created_at": datetime.now().isoformat(),
        "last_session": datetime.now().isoformat(),
        "artifacts": [],
        "notes": [],
    }


def _save_project_metadata(project_dir: Path, metadata: dict[str, object]) -> None:
    """Save project metadata.

    Args:
        project_dir: Project directory
        metadata: Metadata dict to save
    """
    metadata_file = project_dir / PROJECT_METADATA_FILE

    metadata["last_session"] = datetime.now().isoformat()

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def _get_project_stats(project_dir: Path) -> dict[str, object]:
    """Get project statistics.

    Args:
        project_dir: Project directory

    Returns:
        dict with project stats
    """
    stats: dict[str, object] = {
        "project_dir": str(project_dir),
        "exists": project_dir.exists(),
    }

    if not project_dir.exists():
        return stats

    # Count files by type
    file_counts: dict[str, int] = {}
    total_size = 0

    for ext in [".json", ".md", ".wav", ".mp3", ".flac"]:
        files = list(project_dir.rglob(f"*{ext}"))
        file_counts[ext] = len(files)

    # Count directories
    dirs = [d for d in project_dir.rglob("*") if d.is_dir()]
    stats["directories"] = len(dirs)
    stats["file_counts"] = file_counts

    # Check for key files
    key_files = [
        "voice_profile.json",
        "reference_dna.json",
        "friction_report.json",
        "lyrics.json",
        "prompts",
    ]

    present_files = []
    missing_files = []

    for key_file in key_files:
        key_path = project_dir / key_file
        if key_path.exists():
            present_files.append(key_file)
        else:
            missing_files.append(key_file)

    stats["present_artifacts"] = present_files
    stats["missing_artifacts"] = missing_files

    return stats


def _suggest_cleanup(project_dir: Path) -> list[str]:
    """Suggest cleanup actions.

    Args:
        project_dir: Project directory

    Returns:
        list of cleanup suggestions
    """
    suggestions = []

    # Check for large audio files
    large_files: list[tuple[str, int]] = []
    for ext in [".wav", ".mp3", ".flac"]:
        for file_path in project_dir.rglob(f"*{ext}"):
            try:
                size = file_path.stat().st_size
                if size > 50 * 1024 * 1024:  # > 50MB
                    large_files.append((str(file_path.relative_to(project_dir)), size))
            except Exception:
                pass

    if large_files:
        suggestions.append(
            f"Found {len(large_files)} large audio file(s) (>50MB). "
            "Consider archiving or using external storage."
        )

    # Check for orphaned stems
    stems_dir = project_dir / "stems"
    if stems_dir.exists():
        stems_files = list(stems_dir.rglob("*.wav"))
        if len(stems_files) > 10:
            suggestions.append(
                f"Found {len(stems_files)} stem files. Consider cleaning up old stems."
            )

    # Check for duplicate files
    file_hashes: dict[int, list[str]] = {}
    for file_path in project_dir.rglob("*"):
        if file_path.is_file() and file_path.stat().st_size > 1024:
            try:
                # Simple size-based duplicate detection
                size = file_path.stat().st_size
                if size not in file_hashes:
                    file_hashes[size] = []
                file_hashes[size].append(str(file_path.relative_to(project_dir)))
            except Exception:
                pass

    duplicates = [files for files in file_hashes.values() if len(files) > 1]
    if duplicates:
        suggestions.append(
            f"Found {len(duplicates)} potential duplicate file group(s). "
            "Review for cleanup."
        )

    return suggestions


def run(payload: ToolPayload) -> ToolResult:
    """Execute the project_memory tool.

    PRD 11.04: Project memory and cleanup suggestions.

    Args:
        payload: Must contain:
            - project_dir: Project directory

        Optional:
            - action: "get_stats", "suggest_cleanup", "save_note", "get_metadata"

    Returns:
        ToolResult containing project information
    """
    project_dir = payload.get("project_dir")
    if not project_dir:
        raise ValueError("project_dir is required")
    if not isinstance(project_dir, str):
        raise ValueError("project_dir must be a string")

    project_path = Path(project_dir)
    if not project_path.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    action = payload.get("action", "get_stats")

    if action == "get_stats":
        stats = _get_project_stats(project_path)
        return {
            "success": True,
            "stats": stats,
        }

    elif action == "suggest_cleanup":
        suggestions = _suggest_cleanup(project_path)
        return {
            "success": True,
            "suggestions": suggestions,
        }

    elif action == "get_metadata":
        metadata = _get_project_metadata(project_path)
        return {
            "success": True,
            "metadata": metadata,
        }

    elif action == "save_note":
        note = payload.get("note")
        if not note:
            return {
                "success": False,
                "error": "note is required for save_note action",
            }

        metadata = _get_project_metadata(project_path)
        notes_list: list[dict[str, str]] = []
        if "notes" in metadata:
            existing = metadata["notes"]
            if isinstance(existing, list):
                notes_list = existing  # type: ignore
        notes_list.append(
            {
                "text": note,
                "timestamp": datetime.now().isoformat(),
            }
        )
        metadata["notes"] = notes_list
        _save_project_metadata(project_path, metadata)

        return {
            "success": True,
            "message": "Note saved",
        }

    else:
        return {
            "success": False,
            "error": f"Unknown action: {action}",
        }
