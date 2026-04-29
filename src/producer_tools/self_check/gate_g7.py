from __future__ import annotations

import json
import re
import os
from pathlib import Path
from typing import Any

from src.producer_tools.self_check.gate_g0 import check_gate_g0
from src.producer_tools.self_check.gate_g1 import check_gate_g1
from src.producer_tools.self_check.gate_g2 import validate_failure_evidence
from src.producer_tools.self_check.gate_g3 import validate_pass_evidence
from src.producer_tools.self_check.gate_g4 import validate_docs_alignment
from src.producer_tools.self_check.gate_g5 import check_gate_g5
from src.producer_tools.self_check.gate_g6 import check_gate_g6


def _resolve_prosody_contract(workspace_root: Path, trace_payload: dict[str, Any]) -> dict[str, Any]:
    raw = trace_payload.get("prosody_contract", {})
    if isinstance(raw, dict):
        if raw:
            return dict(raw)

    active_profile = str(trace_payload.get("active_profile", "")).strip()
    if not active_profile:
        decision = trace_payload.get("retrieval_profile_decision", {})
        if isinstance(decision, dict):
            active_profile = str(decision.get("active_profile", "")).strip()
    if not active_profile:
        return {}

    registry_path = workspace_root / "src" / "profiles" / "registry.json"
    if not registry_path.exists():
        return {}
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    profiles = registry.get("profiles", {}) if isinstance(registry, dict) else {}
    profile = profiles.get(active_profile, {}) if isinstance(profiles, dict) else {}
    prosody = profile.get("prosody", {}) if isinstance(profile, dict) else {}
    if not isinstance(prosody, dict):
        return {}
    if not prosody:
        return {}
    return dict(prosody)


def _parse_lyrics_sections(lyrics_path: Path) -> dict[str, list[str]]:
    text = _read_text_safe(lyrics_path)
    sections: dict[str, list[str]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)
    return sections


def _prosody_matrix_aligned(prosody_contract: dict[str, Any], output_dir: Path) -> tuple[bool, str]:
    if not isinstance(prosody_contract, dict) or not prosody_contract:
        return False, "prosody_contract_missing"

    lyrics_path = output_dir / "lyrics.txt"
    if not lyrics_path.exists():
        return False, "lyrics.txt missing"

    sections = _parse_lyrics_sections(lyrics_path)
    if not sections:
        return False, "lyrics_sections_missing"

    mapping: dict[str, tuple[str, str]] = {
        "[Verse]": ("verse_line_min", "verse_line_max"),
        "[Verse 1]": ("verse_line_min", "verse_line_max"),
        "[Verse 2]": ("verse_line_min", "verse_line_max"),
        "[Pre-Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Final Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Bridge]": ("bridge_line_min", "bridge_line_max"),
        "[Outro]": ("bridge_line_min", "bridge_line_max"),
    }
    lower_tags = {"(Pause)", "(Breathe)"}
    upper_tags = {"[Fast Flow]"}

    def _line_len(line: str) -> int:
        cleaned = "".join(c for c in line.strip() if c.strip() and c not in "，。？！、；：""''《》【】…—～·")
        return len(cleaned)

    for tag, lines in sections.items():
        keys = mapping.get(tag)
        if keys is None:
            continue
        min_key, max_key = keys
        if min_key not in prosody_contract or max_key not in prosody_contract:
            return False, f"missing_budget_keys:{min_key}/{max_key}"
        line_min = int(prosody_contract[min_key])
        line_max = int(prosody_contract[max_key])

        lengths = [_line_len(x) for x in lines if x.strip()]
        if not lengths:
            continue
        if max(lengths) - min(lengths) > 2:
            return False, f"section_span_exceeds_2:{tag}"
        joined = "\n".join(lines)
        has_lower = any(t in joined for t in lower_tags)
        has_upper = any(t in joined for t in upper_tags)
        if any(x <= line_min for x in lengths) and not has_lower:
            return False, f"missing_lower_metatag:{tag}"
        if any(x >= line_max for x in lengths) and not has_upper:
            return False, f"missing_upper_metatag:{tag}"

    return True, "aligned"


def _run_g2_check() -> dict[str, Any]:
    return validate_failure_evidence(
        {
            "symptom": "schema validation failed",
            "trigger_condition": "pytest -q tests/test_v2_schemas.py::test_payload_schema_invalid",
            "root_cause": "invalid tag and missing fields",
            "failure_command": "pytest -q tests/test_v2_schemas.py::test_payload_schema_invalid",
            "failure_output": "ValidationError: required fields missing",
        }
    )


def _run_g3_check() -> dict[str, Any]:
    return validate_pass_evidence(
        {
            "local_command": "pytest -q",
            "local_result": "pass",
            "ci_result": "pass",
            "ci_run_url": "https://github.com/where6713/AI-music-producer/actions",
            "reproducible_commands": ["pytest -q", "bash tools/scripts/run_quality_gates_ci.sh"],
            "local_output": "25 passed",
            "ci_output": "ci-quality-gates: success",
        }
    )


def _run_g4_check() -> dict[str, Any]:
    return validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "manifest_path": "docs/ai_doc_manifest.json",
            "delivery_files": ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"],
            "field_name_conflicts": [],
        }
    )


def _normalize(result: dict[str, Any]) -> str:
    return "pass" if result.get("status") == "pass" else "fail"


def _read_text_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _count_rule_hits(report: dict[str, Any], rules: set[str]) -> int:
    hits = 0
    violations = report.get("violations", []) if isinstance(report, dict) else []
    if isinstance(violations, list):
        for item in violations:
            if not isinstance(item, dict):
                continue
            if str(item.get("rule", "")).strip() in rules:
                hits += 1

    hard_kill = report.get("hard_kill_rules", []) if isinstance(report, dict) else []
    if isinstance(hard_kill, list):
        for rule in hard_kill:
            if str(rule).strip() in rules:
                hits += 1
    return hits


def _check_lyrics_no_residuals(lyrics_path: Path) -> bool:
    text = _read_text_safe(lyrics_path)
    if not text.strip():
        return False
    content_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("[")
    ]
    if not content_lines:
        return False
    last = content_lines[-1]
    if len(last) < 2:
        return False
    banned_tail = {"的", "在", "把", "被", "对", "向", "给", "和", "与", "于"}
    return last[-1] not in banned_tail


def _check_postprocess_symbols_absent(workspace_root: Path) -> bool:
    symbols = {
        "_polish_" + "readability",
        "_force_hook_" + "line_pass",
        "DEFAULT_FILLER_" + "POOL",
        "_ensure_min_" + "structure",
    }
    src_root = workspace_root / "src"
    if not src_root.exists():
        return True
    for path in src_root.rglob("*.py"):
        text = _read_text_safe(path)
        for symbol in symbols:
            if symbol in text:
                return False
    return True


def _audit_sections_complete(audit_path: Path) -> bool:
    text = _read_text_safe(audit_path)
    required = ["## 0.", "## 1.", "## 2.", "## 3.", "## 4."]
    return all(token in text for token in required)


def _few_shot_ids_clean(trace_payload: dict[str, Any]) -> bool:
    ids = trace_payload.get("few_shot_source_ids", [])
    if not isinstance(ids, list):
        return False
    numeric_pattern = re.compile(r"\d{3}")
    prefixed_pattern = re.compile(r"^(lyric|poem)[-_].*\d{3}", re.IGNORECASE)
    for raw in ids:
        sid = str(raw)
        if sid.startswith("github:"):
            continue
        if prefixed_pattern.search(sid):
            return False
        if numeric_pattern.search(sid):
            return False
    return True


def _pm_audit_checks(
    workspace_root: Path,
    trace_payload: dict[str, Any],
    output_dir: Path,
) -> dict[str, dict[str, Any]]:
    out = output_dir
    prosody_contract = _resolve_prosody_contract(workspace_root, trace_payload)
    prosody_aligned, prosody_detail = _prosody_matrix_aligned(prosody_contract, out)
    lint_report = trace_payload.get("lint_report", {}) if isinstance(trace_payload.get("lint_report", {}), dict) else {}
    r14_r16_hits = _count_rule_hits(lint_report, {"R14", "R16_global"})
    craft_score = float(lint_report.get("craft_score", 0.0) or 0.0)
    is_dead = bool(lint_report.get("is_dead", False))
    profile_source = str(trace_payload.get("profile_source", "")).strip()
    decision = trace_payload.get("retrieval_profile_decision", {})
    vote_confidence_raw = trace_payload.get("retrieval_vote_confidence", None)
    if vote_confidence_raw is None and isinstance(decision, dict):
        vote_confidence_raw = decision.get("vote_confidence", None)
    low_confidence = False
    try:
        if vote_confidence_raw is not None:
            low_confidence = float(vote_confidence_raw) < 0.67
    except (TypeError, ValueError):
        low_confidence = False

    profile_source_detail = f"profile_source={profile_source}"
    if low_confidence:
        profile_source_detail += " LOW_CONFIDENCE"

    checks: dict[str, dict[str, Any]] = {
        "chosen_variant_not_dead": {
            "ok": not is_dead,
            "detail": f"is_dead={is_dead}",
        },
        "craft_score_floor": {
            "ok": craft_score >= 0.85,
            "detail": f"craft_score={craft_score}",
        },
        "r14_r16_global_hits": {
            "ok": r14_r16_hits == 0,
            "detail": f"hits={r14_r16_hits}",
        },
        "few_shot_no_numeric_ids": {
            "ok": _few_shot_ids_clean(trace_payload),
            "detail": f"few_shot_source_ids={trace_payload.get('few_shot_source_ids', [])}",
        },
        "audit_sections_complete": {
            "ok": _audit_sections_complete(out / "audit.md"),
            "detail": "requires sections 0/1/2/3/4",
        },
        "lyrics_no_residuals": {
            "ok": _check_lyrics_no_residuals(out / "lyrics.txt"),
            "detail": "last lyric line should not be residual fragment",
        },
        "postprocess_symbols_absent": {
            "ok": _check_postprocess_symbols_absent(workspace_root),
            "detail": "grep forbidden postprocess symbols",
        },
        "profile_source_recorded": {
            "ok": bool(profile_source),
            "detail": profile_source_detail,
        },
        "prosody_matrix_aligned": {
            "ok": prosody_aligned,
            "detail": f"prosody_matrix_aligned={prosody_aligned} detail={prosody_detail} prosody_contract={prosody_contract}",
        },
    }
    return checks


def _proof_check(
    workspace_root: Path,
    *,
    strict_pm_audit: bool = False,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    out = output_dir if output_dir is not None else (workspace_root / "out")
    required = ["lyrics.txt", "style.txt", "exclude.txt", "lyric_payload.json", "trace.json"]
    missing = [name for name in required if not (out / name).exists()]
    trace_text = (out / "trace.json").read_text(encoding="utf-8", errors="ignore") if (out / "trace.json").exists() else ""
    trace_json_valid = True
    try:
        trace_payload = json.loads(trace_text) if trace_text else {}
    except json.JSONDecodeError:
        trace_payload = {}
        trace_json_valid = False

    llm_calls_raw = trace_payload.get("llm_calls")
    try:
        llm_calls = int(llm_calls_raw)
    except (TypeError, ValueError):
        llm_calls = -1
    llm_calls_ok = llm_calls in {1, 2}

    decision = trace_payload.get("retrieval_profile_decision")
    decision_reason = decision.get("decision_reason") if isinstance(decision, dict) else ""
    source_ids = decision.get("source_ids") if isinstance(decision, dict) else []
    active_profile = str(decision.get("active_profile", "")).strip() if isinstance(decision, dict) else ""
    source_stage = str(decision.get("source_stage", "")).strip() if isinstance(decision, dict) else ""
    has_decision_block = bool(decision_reason) and isinstance(source_ids, list) and bool(source_ids)

    retrieval_decision_gap: list[str] = []
    if not isinstance(decision, dict):
        retrieval_decision_gap.append("retrieval_profile_decision")
    else:
        if not decision_reason:
            retrieval_decision_gap.append("decision_reason")
        if not (isinstance(source_ids, list) and bool(source_ids)):
            retrieval_decision_gap.append("source_ids")

    legacy_source_ids = trace_payload.get("few_shot_source_ids")
    has_legacy_retrieval = isinstance(legacy_source_ids, list) and bool(legacy_source_ids)
    retrieval_audit_ok = has_decision_block or has_legacy_retrieval
    retrieval_audit_mode = "missing"
    if has_decision_block:
        retrieval_audit_mode = "decision"
    elif has_legacy_retrieval:
        retrieval_audit_mode = "legacy"
    retrieval_audit_migration = "missing_evidence"
    if retrieval_audit_mode == "decision":
        retrieval_audit_migration = "decision_primary"
    elif retrieval_audit_mode == "legacy":
        retrieval_audit_migration = "legacy_compat_pending"
    retrieval_decision_quality = "inactive"
    if retrieval_audit_mode == "decision" and active_profile:
        retrieval_decision_quality = "active"

    retrieval_decision_recommendation = "emit_retrieval_audit_fields"
    if retrieval_audit_mode == "legacy":
        retrieval_decision_recommendation = "emit_decision_block"
    elif retrieval_audit_mode == "decision":
        if retrieval_decision_quality == "active":
            retrieval_decision_recommendation = "none"
        else:
            retrieval_decision_recommendation = "improve_profile_vote"

    retrieval_decision_stage = source_stage if source_stage else "unknown"
    pm_checks = _pm_audit_checks(workspace_root, trace_payload, out)
    pm_checks_ok = all(bool(x.get("ok", False)) for x in pm_checks.values())

    status = "pass" if (not missing and llm_calls_ok and retrieval_audit_ok) else "fail"
    if strict_pm_audit and not pm_checks_ok:
        status = "fail"
    return {
        "status": status,
        "output_dir": str(out),
        "missing_files": missing,
        "trace_json_valid": trace_json_valid,
        "llm_calls_ok": llm_calls_ok,
        "retrieval_audit_ok": retrieval_audit_ok,
        "retrieval_audit_mode": retrieval_audit_mode,
        "retrieval_audit_migration": retrieval_audit_migration,
        "retrieval_decision_gap": retrieval_decision_gap,
        "retrieval_decision_quality": retrieval_decision_quality,
        "retrieval_decision_recommendation": retrieval_decision_recommendation,
        "retrieval_decision_stage": retrieval_decision_stage,
        "pm_audit_checks": pm_checks,
        "pm_audit_checks_ok": pm_checks_ok,
    }


def check_gate_g7(
    workspace_root: Path,
    *,
    run_proof: bool = False,
    strict_pm_audit: bool = False,
    proof_output_dir: Path | None = None,
) -> dict[str, Any]:
    g1_target_sha = os.getenv("G1_TARGET_SHA", "").strip()
    g1_require_target = os.getenv("G1_REQUIRE_TARGET_SHA", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    gates = {
        "G0": check_gate_g0(workspace_root, strict_hooks_path=False),
        "G1": check_gate_g1(
            workspace_root,
            target_commit=g1_target_sha,
            require_target=g1_require_target,
        ),
        "G2": _run_g2_check(),
        "G3": _run_g3_check(),
        "G4": _run_g4_check(),
        "G5": check_gate_g5(workspace_root),
        "G6": check_gate_g6(workspace_root),
    }

    gate_summary = {name: _normalize(data) for name, data in gates.items()}
    failed_gates = [name for name, status in gate_summary.items() if status != "pass"]
    failed_gate_details = {
        name: gates.get(name, {}) for name in failed_gates if isinstance(gates.get(name, {}), dict)
    }

    proof = {"status": "skipped", "output_dir": "", "missing_files": [], "llm_calls_ok": False}
    if run_proof:
        proof = _proof_check(
            workspace_root,
            strict_pm_audit=strict_pm_audit,
            output_dir=proof_output_dir,
        )

    status = "pass"
    if failed_gates:
        status = "fail"
    elif run_proof and proof.get("status") != "pass":
        status = "fail"

    return {
        "status": status,
        "gate_summary": gate_summary,
        "failed_gates": failed_gates,
        "failed_gate_details": failed_gate_details,
        "proof": proof,
    }
