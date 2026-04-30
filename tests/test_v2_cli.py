from __future__ import annotations

import subprocess
import sys

import click
import pytest


def _read_local_hooks_path() -> str | None:
    result = subprocess.run(
        ["git", "config", "--local", "--get", "core.hooksPath"],
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.decode("utf-8", errors="replace").strip()
    return value or None


def _restore_local_hooks_path(original: str | None) -> None:
    if original is None:
        subprocess.run(
            ["git", "config", "--local", "--unset", "core.hooksPath"],
            capture_output=True,
            text=False,
            check=False,
        )
        return

    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", original],
        capture_output=True,
        text=False,
        check=False,
    )


def test_cli_status() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "status"],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "ready" in stdout.lower()


def test_cli_docs_alignment_check_reports_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "docs-alignment-check",
            "docs/映月工厂_极简歌词工坊_PRD.json",
            "one law.md",
            "目录框架规范.md",
            "docs/ai_doc_manifest.json",
            "out/lyrics.txt",
            "out/style.txt",
            "out/exclude.txt",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G4 DOCS-ALIGNMENT PASS" in stdout


def test_cli_docs_alignment_check_prints_failed_checks_on_fail() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "docs-alignment-check",
            "docs/映月工厂_极简歌词工坊_PRD.json",
            "one law.md",
            "目录框架规范.md",
            "",
            "out/lyrics.txt",
            "out/style.txt",
            "out/exclude.txt",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 1
    assert "G4 DOCS-ALIGNMENT FAIL" in stdout
    assert "failed_checks: manifest_path" in stdout


def test_cli_self_check_g0_reports_pass() -> None:
    original = _read_local_hooks_path()
    try:
        set_result = subprocess.run(
            ["git", "config", "--local", "core.hooksPath", "tools/githooks"],
            capture_output=True,
            text=False,
            check=False,
        )
        assert set_result.returncode == 0

        result = subprocess.run(
            [sys.executable, "-m", "apps.cli.main", "self-check", "g0"],
            capture_output=True,
            text=False,
            check=False,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        assert result.returncode == 0
        assert "G0 PASS" in stdout
    finally:
        _restore_local_hooks_path(original)


def test_cli_scope_check_g1_reports_pass() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "scope-check", "g1"],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert "G1 SCOPE-CHECK" in stdout


def test_scope_check_uses_env_target_sha(monkeypatch) -> None:
    from apps.cli import main as cli_main

    captured: dict[str, object] = {"target": ""}

    def _fake_check_gate_g1(_workspace_root, target_commit=""):
        captured["target"] = target_commit
        return {"status": "pass", "failed_checks": []}

    monkeypatch.setenv("G1_TARGET_SHA", "prheadsha456")
    monkeypatch.setattr(cli_main, "check_gate_g1", _fake_check_gate_g1)

    cli_main.scope_check("g1")

    assert captured["target"] == "prheadsha456"


def test_cli_failure_evidence_check_requires_failure_output() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "failure-evidence-check",
            "symptom",
            "trigger",
            "root",
            "command",
            "failure output snapshot",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G2 FAILURE-EVIDENCE PASS" in stdout


def test_cli_pass_evidence_check_requires_outputs() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "pass-evidence-check",
            "pytest -q",
            "pass",
            "success",
            "https://github.com/where6713/AI-music-producer/actions/runs/1",
            "pytest -q",
            "python -m apps.cli.main gate-check --all",
            "25 passed",
            "ci-quality-gates: success",
        ],
        capture_output=True,
        text=False,
        check=False,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0
    assert "G3 PASS-EVIDENCE PASS" in stdout


def test_produce_command_prints_ambiguous_profile_candidates(capsys, monkeypatch) -> None:
    from apps.cli import main as cli_main
    from src.profile_router import AmbiguousProfileError

    def _fake_produce(**_kwargs):
        raise AmbiguousProfileError(
            [
                {
                    "profile_id": "urban_introspective",
                    "display_name": "都市内省",
                    "craft_focus": "具象化身体记账 + 场景锚定",
                },
                {
                    "profile_id": "classical_restraint",
                    "display_name": "古风留白",
                    "craft_focus": "意象并置 + 留白 + 典故克制",
                },
            ]
        )

    monkeypatch.setattr(cli_main, "produce_v2", _fake_produce)

    with pytest.raises(click.exceptions.Exit) as err:
        cli_main.produce_command(
            raw_intent="写点东西",
            genre="",
            mood="",
            vocal="any",
            profile="",
            lang="zh-CN",
            out_dir="out",
            verbose=False,
            dry_run=False,
        )

    output = capsys.readouterr().out
    assert err.value.exit_code == 1
    assert "ambiguous profile" in output
    assert "--profile" in output
    assert "urban_introspective" in output


def test_cli_produce_parses_lang_and_outdir_options(monkeypatch) -> None:
    from apps.cli import main as cli_main

    captured: dict[str, object] = {}

    def _fake_produce(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_main, "produce_v2", _fake_produce)
    cli_main._dispatch_produce_from_argv(
        [
            "just write a 2-line haiku only, no verse no chorus",
            "--lang",
            "en-US",
            "--out-dir",
            "out/e2e_pr04_poison",
            "--verbose",
        ]
    )

    assert captured["raw_intent"] == "just write a 2-line haiku only, no verse no chorus"
    assert captured["lang"] == "en-US"
    assert captured["out_dir"] == "out/e2e_pr04_poison"
    assert captured["verbose"] is True


def test_cli_produce_defaults_to_run_id_dir(monkeypatch) -> None:
    from apps.cli import main as cli_main

    captured: dict[str, object] = {}

    def _fake_produce(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_main, "produce_v2", _fake_produce)
    cli_main._dispatch_produce_from_argv([
        "夜里想起旧人",
    ])

    out_dir = str(captured.get("out_dir", ""))
    assert out_dir.startswith("out/runs/")


def test_pm_audit_prints_all_8_checks(monkeypatch, capsys) -> None:
    from apps.cli import main as cli_main

    class _Ctx:
        def __init__(self, args: list[str]) -> None:
            self.args = args

    def _fake_check_gate_g7(*_args, **_kwargs):
        return {
            "status": "pass",
            "proof": {
                "pm_audit_checks": {
                    "chosen_variant_not_dead": {"ok": True, "detail": "is_dead=False"},
                    "craft_score_floor": {"ok": True, "detail": "craft_score=0.9"},
                    "r14_r16_global_hits": {"ok": True, "detail": "hits=0"},
                    "few_shot_no_numeric_ids": {"ok": True, "detail": "ids clean"},
                    "audit_sections_complete": {"ok": True, "detail": "0/1/2/3/4"},
                    "lyrics_no_residuals": {"ok": True, "detail": "pass"},
                    "postprocess_symbols_absent": {"ok": True, "detail": "pass"},
                    "profile_source_recorded": {"ok": True, "detail": "profile_source=corpus_vote"},
                    "prosody_matrix_aligned": {"ok": True, "detail": "aligned"},
                }
            },
        }

    monkeypatch.setattr(cli_main, "check_gate_g7", _fake_check_gate_g7)
    monkeypatch.setattr(cli_main.click, "get_current_context", lambda: _Ctx(["--last"]))
    cli_main.pm_audit()
    out = capsys.readouterr().out

    assert "check_key" in out
    assert "status" in out
    assert "ok" in out
    assert "detail" in out
    assert "chosen_variant_not_dead" in out
    assert "craft_score_floor" in out
    assert "r14_r16_global_hits" in out
    assert "few_shot_no_numeric_ids" in out
    assert "audit_sections_complete" in out
    assert "lyrics_no_residuals" in out
    assert "postprocess_symbols_absent" in out
    assert "profile_source_recorded" in out
    assert "prosody_matrix_aligned" in out
    assert "TOTAL: 9, PASS: 9, FAIL: 0, EXIT: 0" in out


def test_pm_audit_fails_with_exit_1_when_any_check_red(monkeypatch, capsys) -> None:
    from apps.cli import main as cli_main

    class _Ctx:
        def __init__(self, args: list[str]) -> None:
            self.args = args

    def _fake_check_gate_g7(*_args, **_kwargs):
        return {
            "status": "fail",
            "proof": {
                "pm_audit_checks": {
                    "chosen_variant_not_dead": {"ok": True, "detail": "is_dead=False"},
                    "craft_score_floor": {"ok": False, "detail": "craft_score=0.0"},
                    "r14_r16_global_hits": {"ok": True, "detail": "hits=0"},
                    "few_shot_no_numeric_ids": {"ok": True, "detail": "ids clean"},
                    "audit_sections_complete": {"ok": True, "detail": "0/1/2/3/4"},
                    "lyrics_no_residuals": {"ok": True, "detail": "pass"},
                    "postprocess_symbols_absent": {"ok": True, "detail": "pass"},
                    "profile_source_recorded": {"ok": True, "detail": "profile_source=corpus_vote"},
                    "prosody_matrix_aligned": {"ok": True, "detail": "aligned"},
                }
            },
        }

    monkeypatch.setattr(cli_main, "check_gate_g7", _fake_check_gate_g7)
    monkeypatch.setattr(cli_main.click, "get_current_context", lambda: _Ctx([]))
    with pytest.raises(click.exceptions.Exit) as err:
        cli_main.pm_audit()

    out = capsys.readouterr().out
    assert err.value.exit_code == 1
    assert "craft_score_floor" in out
    assert "FAIL" in out
    assert "TOTAL: 9, PASS: 8, FAIL: 1, EXIT: 1" in out


def test_pm_audit_conflict_args_exit_2(monkeypatch, capsys) -> None:
    from apps.cli import main as cli_main

    class _Ctx:
        def __init__(self, args: list[str]) -> None:
            self.args = args

    monkeypatch.setattr(cli_main.click, "get_current_context", lambda: _Ctx(["--last", "--run-id", "abc"]))

    with pytest.raises(click.exceptions.Exit) as err:
        cli_main.pm_audit()

    out = capsys.readouterr().out
    assert err.value.exit_code == 2
    assert "parameter conflict" in out


def test_pm_audit_run_id_not_found_exit_2(monkeypatch, capsys) -> None:
    from apps.cli import main as cli_main

    class _Ctx:
        def __init__(self, args: list[str]) -> None:
            self.args = args

    monkeypatch.setattr(
        cli_main.click,
        "get_current_context",
        lambda: _Ctx(["--run-id", "__missing_run_for_test__"]),
    )

    with pytest.raises(click.exceptions.Exit) as err:
        cli_main.pm_audit()

    out = capsys.readouterr().out
    assert err.value.exit_code == 2
    assert "run-id path not found" in out


def test_pm_audit_exits_zero_when_checks_green_even_if_failed_gates_present(monkeypatch, capsys) -> None:
    from apps.cli import main as cli_main

    class _Ctx:
        def __init__(self, args: list[str]) -> None:
            self.args = args

    def _fake_check_gate_g7(*_args, **_kwargs):
        return {
            "status": "fail",
            "failed_gates": ["G1"],
            "proof": {
                "pm_audit_checks": {
                    "chosen_variant_not_dead": {"ok": True, "detail": "is_dead=False"},
                    "craft_score_floor": {"ok": True, "detail": "craft_score=0.9"},
                    "r14_r16_global_hits": {"ok": True, "detail": "hits=0"},
                    "few_shot_no_numeric_ids": {"ok": True, "detail": "ids clean"},
                    "audit_sections_complete": {"ok": True, "detail": "0/1/2/3/4"},
                    "lyrics_no_residuals": {"ok": True, "detail": "pass"},
                    "postprocess_symbols_absent": {"ok": True, "detail": "pass"},
                    "profile_source_recorded": {"ok": True, "detail": "profile_source=corpus_vote"},
                    "prosody_matrix_aligned": {"ok": True, "detail": "aligned"},
                }
            },
        }

    monkeypatch.setattr(cli_main, "check_gate_g7", _fake_check_gate_g7)
    monkeypatch.setattr(cli_main.click, "get_current_context", lambda: _Ctx([]))

    cli_main.pm_audit()

    out = capsys.readouterr().out
    assert "FAILED_GATES: G1" in out
    assert "TOTAL: 9, PASS: 9, FAIL: 0, EXIT: 0" in out


def test_pm_audit_prints_failed_gate_details_when_available(monkeypatch, capsys) -> None:
    from apps.cli import main as cli_main

    class _Ctx:
        def __init__(self, args: list[str]) -> None:
            self.args = args

    def _fake_check_gate_g7(*_args, **_kwargs):
        return {
            "status": "fail",
            "failed_gates": ["G1"],
            "failed_gate_details": {
                "G1": {"failed_checks": ["commit_scope_gate", "commit_message_format"]}
            },
            "proof": {
                "pm_audit_checks": {
                    "chosen_variant_not_dead": {"ok": True, "detail": "is_dead=False"},
                    "craft_score_floor": {"ok": True, "detail": "craft_score=0.9"},
                    "r14_r16_global_hits": {"ok": True, "detail": "hits=0"},
                    "few_shot_no_numeric_ids": {"ok": True, "detail": "ids clean"},
                    "audit_sections_complete": {"ok": True, "detail": "0/1/2/3/4"},
                    "lyrics_no_residuals": {"ok": True, "detail": "pass"},
                    "postprocess_symbols_absent": {"ok": True, "detail": "pass"},
                    "profile_source_recorded": {"ok": True, "detail": "profile_source=corpus_vote"},
                    "prosody_matrix_aligned": {"ok": True, "detail": "aligned"},
                }
            },
        }

    monkeypatch.setattr(cli_main, "check_gate_g7", _fake_check_gate_g7)
    monkeypatch.setattr(cli_main.click, "get_current_context", lambda: _Ctx([]))

    cli_main.pm_audit()

    out = capsys.readouterr().out
    assert "FAILED_GATES: G1" in out
    assert "FAILED_GATE_DETAIL G1: failed_checks=commit_scope_gate,commit_message_format" in out
