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


def test_validate_g1_scope_pass_for_docs_only_commit_without_gate_scope() -> None:
    result = gate_g1.validate_g1_scope(
        {
            "commit_subject": "docs(pm): add file-level remediation map from today audit",
            "changed_files": [
                "docs/ai_doc_manifest.json",
                "docs/整改task.json",
                "docs/🎵 AI 音乐生成系统产品经理 (PM) Role & Rule.md",
            ],
        }
    )

    assert result["status"] == "pass"
    assert "commit_scope_gate" not in result["failed_checks"]


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


def test_read_git_output_decodes_non_utf8_bytes(monkeypatch, tmp_path) -> None:
    sample = "docs/整改task.json\n".encode("utf-8")

    def _fake_check_output(*_args, **_kwargs):
        return sample

    monkeypatch.setattr(gate_g1.subprocess, "check_output", _fake_check_output)
    output = gate_g1._read_git_output(tmp_path, ["show", "--name-only"])
    assert "整改task.json" in output


def test_check_gate_g1_uses_latest_non_merge_commit_when_head_is_merge(
    monkeypatch, tmp_path
) -> None:
    responses = {
        ("log", "-1", "--pretty=%s"): "Merge branch 'main' into feature\n",
        ("show", "--name-only", "--pretty=", "-1"): "apps/cli/main.py\n",
        ("rev-list", "--no-merges", "-n", "1", "HEAD"): "abc123\n",
        ("show", "-s", "--format=%s", "abc123"): "feat(g7): add pm-audit table with strict exit codes\n",
        ("show", "--name-only", "--pretty=", "abc123"): "apps/cli/main.py\nsrc/producer_tools/self_check/gate_g7.py\n",
    }

    def _fake_read_git_output(_workspace_root, args):
        key = tuple(args)
        if key not in responses:
            raise RuntimeError(f"unexpected args: {args}")
        return responses[key]

    monkeypatch.setattr(gate_g1, "_read_git_output", _fake_read_git_output)

    result = gate_g1.check_gate_g1(tmp_path)

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_check_gate_g1_prefers_pr_head_parent_on_merge_head(monkeypatch, tmp_path) -> None:
    responses = {
        ("log", "-1", "--pretty=%s"): "Merge 123abc into main\n",
        ("show", "--name-only", "--pretty=", "-1"): "apps/cli/main.py\n",
        ("show", "-s", "--format=%s", "HEAD^2"): "test(g7): tighten structural revise contract\n",
        ("show", "--name-only", "--pretty=", "HEAD^2"): "src/main.py\ntests/test_v2_main_variants.py\n",
    }

    def _fake_read_git_output(_workspace_root, args):
        key = tuple(args)
        if key not in responses:
            raise RuntimeError(f"unexpected args: {args}")
        return responses[key]

    monkeypatch.setattr(gate_g1, "_read_git_output", _fake_read_git_output)

    result = gate_g1.check_gate_g1(tmp_path)

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_check_gate_g1_uses_explicit_target_commit_when_provided(monkeypatch, tmp_path) -> None:
    responses = {
        ("show", "-s", "--format=%s", "prsha123"): "fix(g1): pin scope check to pr head sha\n",
        ("show", "--name-only", "--pretty=", "prsha123"): "src/producer_tools/self_check/gate_g1.py\ntests/test_v2_g1.py\n",
    }

    def _fake_read_git_output(_workspace_root, args):
        key = tuple(args)
        if key not in responses:
            raise RuntimeError(f"unexpected args: {args}")
        return responses[key]

    monkeypatch.setattr(gate_g1, "_read_git_output", _fake_read_git_output)

    result = gate_g1.check_gate_g1(tmp_path, target_commit="prsha123")

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_check_gate_g1_uses_env_target_commit(monkeypatch, tmp_path) -> None:
    responses = {
        ("show", "-s", "--format=%s", "envsha789"): "test(g7): add failed gate diagnostics output\n",
        ("show", "--name-only", "--pretty=", "envsha789"): "apps/cli/main.py\ntests/test_v2_cli.py\n",
    }

    def _fake_read_git_output(_workspace_root, args):
        key = tuple(args)
        if key not in responses:
            raise RuntimeError(f"unexpected args: {args}")
        return responses[key]

    monkeypatch.setenv("G1_TARGET_SHA", "envsha789")
    monkeypatch.setattr(gate_g1, "_read_git_output", _fake_read_git_output)

    result = gate_g1.check_gate_g1(tmp_path)

    assert result["status"] == "pass"
    assert result["failed_checks"] == []
