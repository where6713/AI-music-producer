from __future__ import annotations

from src.producer_tools.self_check import gate_g1


def test_validate_g1_scope_pass() -> None:
    result = gate_g1.validate_g1_scope(
        {
            "commit_subject": "feat(g1): add scope validator and cli entry",
            "changed_files": [
                "src/producer_tools/self_check/gate_g1.py",
                "apps/cli/main.py",
                "tests/test_v2_g1.py",
            ],
        }
    )

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_validate_g1_scope_fail_for_invalid_commit_format() -> None:
    result = gate_g1.validate_g1_scope(
        {
            "commit_subject": "bad commit title",
            "changed_files": ["src/producer_tools/self_check/gate_g1.py"],
        }
    )

    assert result["status"] == "fail"
    assert "commit_message_format" in result["failed_checks"]


def test_validate_g1_scope_fail_for_non_g1_scope() -> None:
    result = gate_g1.validate_g1_scope(
        {
            "commit_subject": "feat(core): add failure evidence checker",
            "changed_files": ["src/producer_tools/self_check/gate_g1.py"],
        }
    )

    assert result["status"] == "fail"
    assert "commit_scope_gate" in result["failed_checks"]


def test_validate_g1_scope_pass_for_later_gate_scope() -> None:
    result = gate_g1.validate_g1_scope(
        {
            "commit_subject": "feat(g3): tighten pass evidence contract",
            "changed_files": ["src/producer_tools/self_check/gate_g3.py"],
        }
    )

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_validate_g1_scope_fail_when_mixed_gitkeep_cleanup() -> None:
    result = gate_g1.validate_g1_scope(
        {
            "commit_subject": "feat(g1): add scope validator and cli entry",
            "changed_files": [
                "src/producer_tools/self_check/gate_g1.py",
                "apps/.gitkeep",
            ],
        }
    )

    assert result["status"] == "fail"
    assert "mixed_gitkeep_cleanup" in result["failed_checks"]


def test_check_gate_g1_pass_with_repo_head(monkeypatch, tmp_path) -> None:
    commit_subject = "feat(g1): add scope validator and cli entry\n"
    changed = "src/producer_tools/self_check/gate_g1.py\napps/cli/main.py\n"

    def _fake_read_git_output(_workspace_root, args):
        if args[:2] == ["log", "-1"]:
            return commit_subject
        return changed

    monkeypatch.setattr(gate_g1, "_read_git_output", _fake_read_git_output)
    result = gate_g1.check_gate_g1(tmp_path)

    assert result["status"] == "pass"


def test_check_gate_g1_fail_when_git_unavailable(monkeypatch, tmp_path) -> None:
    def _raise(*_args, **_kwargs):
        raise RuntimeError("git error")

    monkeypatch.setattr(gate_g1, "_read_git_output", _raise)
    result = gate_g1.check_gate_g1(tmp_path)

    assert result["status"] == "fail"
    assert result["failed_checks"] == ["git_metadata_unavailable"]
