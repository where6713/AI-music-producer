from __future__ import annotations

from tools.scripts.pm_auto_worker import parse_task_comment


def test_parse_task_comment_matches_task_tag_without_auto_run() -> None:
    body = "[TASK-G4-004] please handle this now"
    parsed = parse_task_comment("123", body)
    assert parsed is not None
    assert parsed.task_tag == "TASK-G4-004"
    assert parsed.auto_run == ""


def test_parse_task_comment_extracts_auto_run_command() -> None:
    body = "[PM-AUTO-TASK-009]\nAUTO_RUN: python -m pytest -q"
    parsed = parse_task_comment("124", body)
    assert parsed is not None
    assert parsed.task_tag == "PM-AUTO-TASK-009"
    assert parsed.auto_run == "python -m pytest -q"
