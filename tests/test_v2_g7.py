from __future__ import annotations

import json
from pathlib import Path

from src.producer_tools.self_check.gate_g7 import _proof_check


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
