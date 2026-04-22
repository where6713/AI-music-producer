from __future__ import annotations

import json

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
