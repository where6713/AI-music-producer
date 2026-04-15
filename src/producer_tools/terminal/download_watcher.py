"""Download watcher tool for auto-import.

PRD 8.2: Auto-import from watchdog downloads.

Features:
- Watch Windows downloads directory for new audio files
- Auto-import files matching project patterns
- Notify agent of new takes
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..contracts import ToolPayload, ToolResult

if TYPE_CHECKING:
    from collections.abc import Mapping

TOOL_NAME = "download_watcher"

logger = logging.getLogger(__name__)

# Default Windows downloads path
DEFAULT_DOWNLOADS_PATH = str(Path.home() / "Downloads")

# Audio file extensions to watch
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}


def _state_file(project_dir: Path) -> Path:
    return project_dir / ".state" / "download_watcher_state.json"


def _load_state(project_dir: Path) -> dict[str, object]:
    path = _state_file(project_dir)
    if not path.exists():
        return {"processed": {}, "queue": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            processed = data.get("processed", {})
            queue = data.get("queue", [])
            return {
                "processed": processed if isinstance(processed, dict) else {},
                "queue": queue if isinstance(queue, list) else [],
            }
    except Exception:
        pass
    return {"processed": {}, "queue": []}


def _save_state(project_dir: Path, state: dict[str, object]) -> None:
    path = _state_file(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _fingerprint_file(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _generate_take_filename(original_path: Path, project_dir: Path) -> Path:
    """Generate timestamped take filename.

    Args:
        original_path: Original downloaded file path
        project_dir: Project directory

    Returns:
        Path for the new take file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = original_path.stem
    suffix = original_path.suffix.lower()
    new_name = f"{timestamp}_take_{stem}{suffix}"
    return project_dir / "takes" / new_name


def _is_suno_file(filename: str) -> bool:
    """Check if filename looks like a Suno download.

    Args:
        filename: Name of the file

    Returns:
        True if filename suggests Suno origin
    """
    filename_lower = filename.lower()
    return "suno" in filename_lower or filename_lower.startswith("audio_")


def _should_auto_import(filename: str) -> bool:
    """Check if file should be auto-imported.

    Args:
        filename: Name of the file

    Returns:
        True if file matches auto-import criteria
    """
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        return False

    # Check if Suno file
    if _is_suno_file(filename):
        return True

    # Could add more pattern matching here
    return False


def run(payload: ToolPayload) -> ToolResult:
    """Execute the download_watcher tool.

    PRD 8.2: Watch downloads directory and auto-import new audio files.

    Args:
        payload: Must contain:
            - project_dir: Project directory to import into

        Optional:
            - watch_dir: Directory to watch (default: Windows Downloads)
            - auto_import: Whether to auto-import (default: True)

    Returns:
        ToolResult containing:
            - status: Watcher status
            - imported_files: List of files imported
            - message: Status message
    """
    project_dir = payload.get("project_dir")
    if not project_dir:
        raise ValueError("project_dir is required")
    if not isinstance(project_dir, str):
        raise ValueError("project_dir must be a string")

    project_path = Path(project_dir)
    if not project_path.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    watch_dir = payload.get("watch_dir", DEFAULT_DOWNLOADS_PATH)
    if not isinstance(watch_dir, str):
        watch_dir = DEFAULT_DOWNLOADS_PATH

    auto_import = payload.get("auto_import", True)
    if not isinstance(auto_import, bool):
        auto_import = True

    auto_post_process = payload.get("auto_post_process", False)
    if not isinstance(auto_post_process, bool):
        auto_post_process = False

    post_process_adapter = payload.get("post_process_adapter")
    adapter_callable = post_process_adapter if callable(post_process_adapter) else None

    # Check for new files in downloads directory
    watch_path = Path(watch_dir)
    if not watch_path.exists():
        return {
            "success": False,
            "error": f"Watch directory not found: {watch_dir}",
            "status": "error",
        }

    imported_files: list[str] = []
    skipped_files: list[str] = []
    skipped_duplicates: list[str] = []
    post_process_reports: list[dict[str, object]] = []
    queue: list[dict[str, object]] = []
    state = _load_state(project_path)
    processed_raw = state.get("processed", {}) if isinstance(state, dict) else {}
    processed: dict[str, object] = (
        processed_raw if isinstance(processed_raw, dict) else {}
    )

    try:
        # Scan for new audio files
        for entry in os.scandir(watch_dir):
            if not entry.is_file():
                continue

            filename = entry.name
            if _should_auto_import(filename):
                src_path = Path(entry.path)
                fp = _fingerprint_file(src_path)
                if fp in processed:
                    skipped_duplicates.append(str(src_path))
                    queue.append(
                        {
                            "event_id": fp,
                            "source": str(src_path),
                            "status": "skipped_duplicate",
                        }
                    )
                    continue

                queue_item: dict[str, object] = {
                    "event_id": fp,
                    "source": str(src_path),
                    "status": "detected",
                }
                queue.append(queue_item)
                dst_path = _generate_take_filename(src_path, project_path)

                # Create takes directory if needed
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                if auto_import:
                    shutil.copy2(src_path, dst_path)
                    imported_files.append(str(dst_path))
                    queue_item["take_path"] = str(dst_path)
                    queue_item["status"] = "imported"
                    processed[fp] = {
                        "source": str(src_path),
                        "take_path": str(dst_path),
                        "status": "imported",
                    }
                else:
                    skipped_files.append(str(src_path))
                    queue_item["status"] = "detected"

        if imported_files:
            if auto_post_process:
                if adapter_callable is None:
                    try:
                        from ..business import post_processor

                        adapter_callable = post_processor.run
                    except Exception:
                        adapter_callable = None

                if adapter_callable is not None:
                    for imported in imported_files:
                        try:
                            report = adapter_callable(
                                {
                                    "input_path": imported,
                                    "output_dir": str(project_path / "masters"),
                                }
                            )
                            post_process_reports.append(
                                {
                                    "take_path": imported,
                                    "status": "completed",
                                    "result": report,
                                }
                            )
                            for item in queue:
                                if item.get("take_path") == imported:
                                    item["status"] = "processed"
                                    break
                        except Exception as exc:
                            post_process_reports.append(
                                {
                                    "take_path": imported,
                                    "status": "failed",
                                    "error": str(exc),
                                }
                            )
                            for item in queue:
                                if item.get("take_path") == imported:
                                    item["status"] = "processing_failed"
                                    item["error"] = str(exc)
                                    break

            status = "imported"
            if post_process_reports:
                status = "imported_and_processed"

            state["processed"] = processed
            state["queue"] = queue
            _save_state(project_path, state)

            return {
                "success": True,
                "status": status,
                "imported_files": imported_files,
                "skipped_duplicates": skipped_duplicates,
                "post_process_reports": post_process_reports,
                "queue": queue,
                "message": f"Auto-imported {len(imported_files)} file(s)",
            }
        elif skipped_files:
            state["processed"] = processed
            state["queue"] = queue
            _save_state(project_path, state)
            return {
                "success": True,
                "status": "detected",
                "detected_files": skipped_files,
                "queue": queue,
                "message": f"Detected {len(skipped_files)} file(s), auto-import disabled",
            }
        elif skipped_duplicates:
            state["processed"] = processed
            state["queue"] = queue
            _save_state(project_path, state)
            return {
                "success": True,
                "status": "deduplicated",
                "imported_files": [],
                "skipped_duplicates": skipped_duplicates,
                "queue": queue,
                "message": f"Skipped {len(skipped_duplicates)} duplicate file(s)",
            }
        else:
            state["processed"] = processed
            state["queue"] = queue
            _save_state(project_path, state)
            return {
                "success": True,
                "status": "no_files",
                "queue": queue,
                "message": "No new audio files detected",
            }

    except Exception as e:
        logger.exception("Download watcher failed")
        return {
            "success": False,
            "error": str(e),
            "status": "error",
        }
