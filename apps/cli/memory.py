from __future__ import annotations

from pathlib import Path

MAX_SECTION_LINES = 12


def _load_latest_section(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    indices = [index for index, line in enumerate(lines) if line.startswith("## [")]
    if indices:
        section = lines[indices[-1] :]
    else:
        section = lines

    while section and not section[0].strip():
        section = section[1:]
    while section and not section[-1].strip():
        section = section[:-1]
    if not section:
        return ""
    if len(section) > MAX_SECTION_LINES:
        section = section[:MAX_SECTION_LINES]
    return "\n".join(section)


def _read_latest_from_file(path: Path) -> str:
    if not path.exists():
        return ""
    return _load_latest_section(path.read_text(encoding="utf-8"))


def _format_display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def get_project_memory_context(base_path: Path | None = None) -> str:
    root = base_path or Path.cwd()
    notepad_dir = root / ".sisyphus" / "notepads" / "infrastructure-setup"
    entries = [
        ("LEARNINGS", notepad_dir / "learnings.md"),
        ("ISSUES", notepad_dir / "issues.md"),
    ]
    parts: list[str] = []
    for label, path in entries:
        latest = _read_latest_from_file(path)
        if latest:
            display_path = _format_display_path(path, root)
            parts.append(f"{label} ({display_path}):\n{latest}")
    return "\n\n".join(parts).strip()
