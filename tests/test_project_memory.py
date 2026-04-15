from pathlib import Path

from apps.cli.memory import get_project_memory_context


def test_project_memory_context_uses_latest_sections(tmp_path: Path) -> None:
    notepad_dir = tmp_path / ".sisyphus" / "notepads" / "infrastructure-setup"
    notepad_dir.mkdir(parents=True)
    learnings_path = notepad_dir / "learnings.md"
    issues_path = notepad_dir / "issues.md"

    _ = learnings_path.write_text(
        """
## Notes

## [2026-01-01T00:00:00+00:00] Task: Old learnings
- earlier note

## [2026-01-02T00:00:00+00:00] Task: New learnings
- latest note
""".strip(),
        encoding="utf-8",
    )
    _ = issues_path.write_text(
        """
## Notes

## [2026-01-01T00:00:00+00:00] Task: Old issues
- earlier issue

## [2026-01-02T00:00:00+00:00] Task: New issues
- latest issue
""".strip(),
        encoding="utf-8",
    )

    summary = get_project_memory_context(base_path=tmp_path)

    assert "LEARNINGS" in summary
    assert "ISSUES" in summary
    assert "Task: New learnings" in summary
    assert "Task: Old learnings" not in summary
    assert "Task: New issues" in summary
    assert "Task: Old issues" not in summary
