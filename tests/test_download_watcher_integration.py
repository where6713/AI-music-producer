from __future__ import annotations

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


def test_download_watcher_auto_post_process_with_adapter(tmp_path: Path) -> None:
    from producer_tools.terminal import download_watcher

    project_dir = tmp_path / "project"
    watch_dir = tmp_path / "downloads"
    project_dir.mkdir(parents=True, exist_ok=True)
    watch_dir.mkdir(parents=True, exist_ok=True)

    sample_take = watch_dir / "suno_take_demo.mp3"
    sample_take.write_bytes(b"fake-audio-bytes")

    calls: list[dict[str, object]] = []

    def _fake_post_adapter(payload: dict[str, object]) -> dict[str, object]:
        calls.append(payload)
        return {
            "post_process_report": {"status": "ok"},
            "master_wav": str(project_dir / "masters" / "master_001.wav"),
        }

    result = download_watcher.run(
        {
            "project_dir": str(project_dir),
            "watch_dir": str(watch_dir),
            "auto_import": True,
            "auto_post_process": True,
            "post_process_adapter": _fake_post_adapter,
        }
    )

    assert result.get("success") is True
    assert result.get("status") in {"imported", "imported_and_processed"}
    imported_files = result.get("imported_files", [])
    assert isinstance(imported_files, list)
    assert len(imported_files) == 1
    reports = result.get("post_process_reports", [])
    assert isinstance(reports, list)
    assert len(reports) == 1
    assert calls, "post process adapter should be invoked"


def test_download_watcher_is_idempotent_across_runs(tmp_path: Path) -> None:
    from producer_tools.terminal import download_watcher

    project_dir = tmp_path / "project"
    watch_dir = tmp_path / "downloads"
    project_dir.mkdir(parents=True, exist_ok=True)
    watch_dir.mkdir(parents=True, exist_ok=True)

    sample_take = watch_dir / "suno_repeat_take.mp3"
    sample_take.write_bytes(b"same-bytes")

    first = download_watcher.run(
        {
            "project_dir": str(project_dir),
            "watch_dir": str(watch_dir),
            "auto_import": True,
        }
    )
    second = download_watcher.run(
        {
            "project_dir": str(project_dir),
            "watch_dir": str(watch_dir),
            "auto_import": True,
        }
    )

    assert first.get("success") is True
    assert len(first.get("imported_files", [])) == 1
    assert second.get("success") is True
    assert second.get("status") in {"no_files", "deduplicated"}
    assert len(second.get("imported_files", [])) == 0
    duplicates = second.get("skipped_duplicates", [])
    assert isinstance(duplicates, list)
    assert duplicates, "second run should report duplicate skip"


def test_download_watcher_exposes_queue_state_machine(tmp_path: Path) -> None:
    from producer_tools.terminal import download_watcher

    project_dir = tmp_path / "project"
    watch_dir = tmp_path / "downloads"
    project_dir.mkdir(parents=True, exist_ok=True)
    watch_dir.mkdir(parents=True, exist_ok=True)

    sample_take = watch_dir / "suno_queue_take.mp3"
    sample_take.write_bytes(b"queue-bytes")

    def _fake_post(payload: dict[str, object]) -> dict[str, object]:
        _ = payload
        return {"post_process_report": {"status": "ok"}}

    result = download_watcher.run(
        {
            "project_dir": str(project_dir),
            "watch_dir": str(watch_dir),
            "auto_import": True,
            "auto_post_process": True,
            "post_process_adapter": _fake_post,
        }
    )

    queue = result.get("queue", [])
    assert isinstance(queue, list)
    assert queue, "queue must be emitted"
    states = {str(item.get("status", "")) for item in queue if isinstance(item, dict)}
    assert "processed" in states or "processing_failed" in states
