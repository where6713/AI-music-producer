from __future__ import annotations

import json
from pathlib import Path

from src.producer_tools.self_check.gate_g7 import _proof_check, check_gate_g7


def test_proof_check_pass_with_retrieval_decision(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "retrieval_profile_decision": {
                    "profile_vote": "urban_introspective",
                    "vote_confidence": 2 / 3,
                    "active_profile": "urban_introspective",
                    "decision_reason": "activated",
                    "source_stage": "revise",
                    "source_ids": ["lyric-modern-101", "lyric-modern-102"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "pass"
    assert result["llm_calls_ok"] is True
    assert result["retrieval_audit_ok"] is True
    assert result["retrieval_audit_mode"] == "decision"
    assert result["retrieval_audit_migration"] == "decision_primary"
    assert result["retrieval_decision_quality"] == "active"
    assert result["retrieval_decision_recommendation"] == "none"
    assert result["retrieval_decision_stage"] == "revise"


def test_proof_check_fail_without_retrieval_decision(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps({"llm_calls": 1}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "fail"
    assert result["llm_calls_ok"] is True
    assert result["retrieval_audit_ok"] is False
    assert result["retrieval_audit_mode"] == "missing"
    assert result["retrieval_audit_migration"] == "missing_evidence"
    assert result["retrieval_decision_recommendation"] == "emit_retrieval_audit_fields"
    assert result["retrieval_decision_stage"] == "unknown"


def test_proof_check_pass_with_legacy_retrieval_source_ids(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "few_shot_source_ids": ["lyric-modern-102", "poem-jys-001", "poem-cy-002"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "pass"
    assert result["llm_calls_ok"] is True
    assert result["retrieval_audit_ok"] is True
    assert result["retrieval_audit_mode"] == "legacy"
    assert result["retrieval_audit_migration"] == "legacy_compat_pending"
    assert "retrieval_profile_decision" in result["retrieval_decision_gap"]
    assert result["retrieval_decision_recommendation"] == "emit_decision_block"
    assert result["retrieval_decision_stage"] == "unknown"


def test_proof_check_fail_when_llm_calls_out_of_contract(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 10,
                "few_shot_source_ids": ["lyric-modern-102"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "fail"
    assert result["llm_calls_ok"] is False


def test_proof_check_fail_when_legacy_retrieval_ids_empty(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 1,
                "few_shot_source_ids": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "fail"
    assert result["llm_calls_ok"] is True
    assert result["retrieval_audit_ok"] is False
    assert result["retrieval_audit_mode"] == "missing"
    assert result["retrieval_audit_migration"] == "missing_evidence"


def test_proof_check_fail_when_trace_json_invalid(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text("{ invalid json", encoding="utf-8")

    result = _proof_check(tmp_path)

    assert result["status"] == "fail"
    assert result["trace_json_valid"] is False
    assert result["llm_calls_ok"] is False
    assert result["retrieval_audit_ok"] is False
    assert result["retrieval_audit_mode"] == "missing"
    assert result["retrieval_audit_migration"] == "missing_evidence"


def test_proof_check_prefers_decision_mode_when_both_formats_exist(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "few_shot_source_ids": ["lyric-modern-102"],
                "retrieval_profile_decision": {
                    "profile_vote": "urban_introspective",
                    "vote_confidence": 0.8,
                    "active_profile": "urban_introspective",
                    "decision_reason": "activated",
                    "source_stage": "initial",
                    "source_ids": ["lyric-modern-102"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "pass"
    assert result["retrieval_audit_ok"] is True
    assert result["retrieval_audit_mode"] == "decision"
    assert result["retrieval_audit_migration"] == "decision_primary"
    assert result["retrieval_decision_gap"] == []
    assert result["retrieval_decision_quality"] == "active"
    assert result["retrieval_decision_stage"] == "initial"


def test_proof_check_marks_decision_quality_inactive_when_no_active_profile(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
        (out / name).write_text("ok\n", encoding="utf-8")

    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "retrieval_profile_decision": {
                    "profile_vote": "",
                    "vote_confidence": 0.0,
                    "active_profile": "",
                    "decision_reason": "no_profile_vote",
                    "source_stage": "revise",
                    "source_ids": ["lyric-modern-101", "poem-jys-001"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _proof_check(tmp_path)

    assert result["status"] == "pass"
    assert result["retrieval_audit_mode"] == "decision"
    assert result["retrieval_decision_quality"] == "inactive"
    assert result["retrieval_decision_recommendation"] == "improve_profile_vote"
    assert result["retrieval_decision_stage"] == "revise"


def test_check_gate_g7_includes_failed_gate_details(monkeypatch, tmp_path) -> None:
    def _ok(*_args, **_kwargs):
        return {"status": "pass"}

    def _g1_fail(*_args, **_kwargs):
        return {
            "status": "fail",
            "failed_checks": ["commit_scope_gate"],
            "commit_subject": "Merge deadbeef into main",
            "changed_files": ["apps/cli/main.py"],
        }

    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g0", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g1", _g1_fail)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g2_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g3_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g4_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g5", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g6", _ok)

    result = check_gate_g7(tmp_path, run_proof=False)

    assert result["status"] == "fail"
    assert result["failed_gates"] == ["G1"]
    details = result.get("failed_gate_details", {})
    assert isinstance(details, dict)
    assert details["G1"]["failed_checks"] == ["commit_scope_gate"]


def test_check_gate_g7_passes_env_target_sha_to_g1(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {"target": ""}

    def _ok(*_args, **_kwargs):
        return {"status": "pass"}

    def _g1_capture(_workspace_root, target_commit="", require_target=False):
        captured["target"] = target_commit
        return {"status": "pass", "failed_checks": []}

    monkeypatch.setenv("G1_TARGET_SHA", "abc123head")
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g0", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g1", _g1_capture)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g2_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g3_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g4_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g5", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g6", _ok)

    result = check_gate_g7(tmp_path, run_proof=False)

    assert result["status"] == "pass"
    assert captured["target"] == "abc123head"


def test_check_gate_g7_passes_require_target_flag_to_g1(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {"target": "", "require": None}

    def _ok(*_args, **_kwargs):
        return {"status": "pass"}

    def _g1_capture(_workspace_root, target_commit="", require_target=False):
        captured["target"] = target_commit
        captured["require"] = require_target
        return {"status": "pass", "failed_checks": []}

    monkeypatch.setenv("G1_TARGET_SHA", "abc123head")
    monkeypatch.setenv("G1_REQUIRE_TARGET_SHA", "true")
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g0", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g1", _g1_capture)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g2_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g3_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7._run_g4_check", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g5", _ok)
    monkeypatch.setattr("src.producer_tools.self_check.gate_g7.check_gate_g6", _ok)

    result = check_gate_g7(tmp_path, run_proof=False)

    assert result["status"] == "pass"
    assert captured["target"] == "abc123head"
    assert captured["require"] is True


def test_pm_audit_proof_reports_decision_mode_when_trace_has_decision_block() -> None:
    trace_path = Path("out") / "trace.json"
    original = trace_path.read_text(encoding="utf-8") if trace_path.exists() else None

    decision_trace = {
        "llm_calls": 2,
        "few_shot_source_ids": ["lyric-modern-101", "poem-jys-001"],
        "retrieval_profile_decision": {
            "profile_vote": "urban_introspective",
            "vote_confidence": 2 / 3,
            "active_profile": "urban_introspective",
            "decision_reason": "activated",
            "source_ids": ["lyric-modern-101", "poem-jys-001"],
        },
    }

    try:
        Path("out").mkdir(parents=True, exist_ok=True)
        for name in ("lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json"):
            fp = Path("out") / name
            if not fp.exists():
                fp.write_text("ok\n", encoding="utf-8")

        trace_path.write_text(json.dumps(decision_trace, ensure_ascii=False, indent=2), encoding="utf-8")
        result = _proof_check(Path.cwd())
        assert result["status"] == "pass"
        assert result["retrieval_audit_mode"] == "decision"
        assert result["retrieval_audit_migration"] == "decision_primary"
    finally:
        if original is None:
            trace_path.unlink(missing_ok=True)
        else:
            trace_path.write_text(original, encoding="utf-8")


def test_proof_check_pm_audit_checks_cover_required_items(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lyrics.txt").write_text("[Verse 1]\nline one\nline two\nline three\nline four\nline five\n\n[Chorus]\nline one\nline two\nline three\nline four\nline five\n", encoding="utf-8")
    (out / "style.txt").write_text("ok\n", encoding="utf-8")
    (out / "exclude.txt").write_text("ok\n", encoding="utf-8")
    (out / "lyric_payload.json").write_text("{}\n", encoding="utf-8")
    (out / "audit.md").write_text("## 0.\n## 1.\n## 2.\n## 3.\n## 4.\n", encoding="utf-8")
    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "profile_source": "corpus_vote",
                "few_shot_source_ids": ["lyric-modern-aa", "poem-cr-bb"],
                "retrieval_profile_decision": {
                    "profile_vote": "urban_introspective",
                    "vote_confidence": 0.9,
                    "active_profile": "urban_introspective",
                    "decision_reason": "activated",
                    "source_stage": "initial",
                    "source_ids": ["lyric-modern-aa", "poem-cr-bb"],
                },
                "lint_report": {
                    "craft_score": 0.9,
                    "is_dead": False,
                    "violations": [],
                    "hard_kill_rules": [],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "dummy.py").write_text("def ok():\n    return 1\n", encoding="utf-8")

    result = _proof_check(tmp_path, strict_pm_audit=True)

    assert result["status"] == "pass"
    assert result["pm_audit_checks_ok"] is True
    checks = result["pm_audit_checks"]
    assert len(checks) == 8
    assert all(bool(item.get("ok", False)) for item in checks.values())


def test_pm_audit_allows_github_source_ids_with_digits(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lyrics.txt").write_text("[Verse 1]\nline one\nline two\nline three\nline four\nline five\n", encoding="utf-8")
    (out / "style.txt").write_text("ok\n", encoding="utf-8")
    (out / "exclude.txt").write_text("ok\n", encoding="utf-8")
    (out / "lyric_payload.json").write_text("{}\n", encoding="utf-8")
    (out / "audit.md").write_text("## 0.\n## 1.\n## 2.\n## 3.\n## 4.\n", encoding="utf-8")
    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "profile_source": "corpus_vote",
                "few_shot_source_ids": [
                    "github:gaussic/Chinese-Lyric-Corpus:path/track_123.txt",
                    "github:gaussic/Chinese-Lyric-Corpus:path/track_456.txt",
                ],
                "lint_report": {
                    "craft_score": 0.9,
                    "is_dead": False,
                    "violations": [],
                    "hard_kill_rules": [],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "dummy.py").write_text("def ok():\n    return 1\n", encoding="utf-8")

    result = _proof_check(tmp_path, strict_pm_audit=True)

    assert result["pm_audit_checks"]["few_shot_no_numeric_ids"]["ok"] is True


def test_check_gate_g7_uses_injected_proof_output_dir(tmp_path) -> None:
    out = tmp_path / "custom_out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lyrics.txt").write_text("[Verse 1]\nline one\nline two\n", encoding="utf-8")
    (out / "style.txt").write_text("ok\n", encoding="utf-8")
    (out / "exclude.txt").write_text("ok\n", encoding="utf-8")
    (out / "lyric_payload.json").write_text("{}\n", encoding="utf-8")
    (out / "audit.md").write_text("## 0.\n## 1.\n## 2.\n## 3.\n## 4.\n", encoding="utf-8")
    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "profile_source": "corpus_vote",
                "few_shot_source_ids": ["lyric-modern-aa", "poem-cr-bb"],
                "retrieval_profile_decision": {
                    "profile_vote": "urban_introspective",
                    "vote_confidence": 0.9,
                    "active_profile": "urban_introspective",
                    "decision_reason": "activated",
                    "source_stage": "initial",
                    "source_ids": ["lyric-modern-aa", "poem-cr-bb"],
                },
                "lint_report": {
                    "craft_score": 0.9,
                    "is_dead": False,
                    "violations": [],
                    "hard_kill_rules": [],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "dummy.py").write_text("def ok():\n    return 1\n", encoding="utf-8")

    result = check_gate_g7(
        tmp_path,
        run_proof=True,
        strict_pm_audit=True,
        proof_output_dir=out,
    )

    assert result["proof"]["output_dir"] == str(out)
    assert result["proof"]["status"] == "pass"


def test_pm_audit_profile_source_detail_marks_low_confidence(tmp_path) -> None:
    out = tmp_path / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lyrics.txt").write_text("[Verse 1]\nline one\nline two\nline three\n", encoding="utf-8")
    (out / "style.txt").write_text("ok\n", encoding="utf-8")
    (out / "exclude.txt").write_text("ok\n", encoding="utf-8")
    (out / "lyric_payload.json").write_text("{}\n", encoding="utf-8")
    (out / "audit.md").write_text("## 0.\n## 1.\n## 2.\n## 3.\n## 4.\n", encoding="utf-8")
    (out / "trace.json").write_text(
        json.dumps(
            {
                "llm_calls": 2,
                "profile_source": "corpus_vote",
                "retrieval_profile_decision": {
                    "profile_vote": "urban_introspective",
                    "vote_confidence": 0.5,
                    "active_profile": "",
                    "decision_reason": "insufficient_confidence",
                    "source_stage": "initial",
                    "source_ids": ["lyric-modern-aa", "poem-cr-bb"],
                },
                "few_shot_source_ids": ["lyric-modern-aa", "poem-cr-bb"],
                "lint_report": {
                    "craft_score": 0.9,
                    "is_dead": False,
                    "violations": [],
                    "hard_kill_rules": [],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "dummy.py").write_text("def ok():\n    return 1\n", encoding="utf-8")

    result = _proof_check(tmp_path, strict_pm_audit=True, output_dir=out)
    detail = result["pm_audit_checks"]["profile_source_recorded"]["detail"]

    assert "profile_source=corpus_vote" in detail
    assert "LOW_CONFIDENCE" in detail
