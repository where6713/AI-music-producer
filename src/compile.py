from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas import LyricPayload


class StructuralIncompleteError(RuntimeError):
    pass


def _validate_required_sections(payload: LyricPayload) -> None:
    has_verse = False
    has_chorus = False

    for section in payload.lyrics_by_section:
        tag = section.tag.strip().lower()
        line_count = len(section.lines)
        if tag.startswith("[verse"):
            if line_count >= 5:
                has_verse = True
        if tag.startswith("[chorus"):
            if line_count >= 5:
                has_chorus = True

    if not has_verse:
        raise StructuralIncompleteError(
            "missing required section: Verse with at least 5 lines"
        )
    if not has_chorus:
        raise StructuralIncompleteError(
            "missing required section: Chorus with at least 5 lines"
        )


def _count_required_sections(payload: LyricPayload) -> tuple[int, int]:
    verse_count = 0
    chorus_count = 0
    for section in payload.lyrics_by_section:
        tag = section.tag.strip().lower()
        if tag.startswith("[verse") and len(section.lines) >= 5:
            verse_count += 1
        if tag.startswith("[chorus") and len(section.lines) >= 5:
            chorus_count += 1
    return verse_count, chorus_count


def _safe_float(value: object, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _infer_profile_vote_from_source_ids(source_ids: list[str]) -> str:
    modern_hits = sum(1 for x in source_ids if x.startswith("lyric-modern-"))
    classical_hits = sum(1 for x in source_ids if x.startswith("poem-"))
    if modern_hits >= classical_hits and modern_hits > 0:
        return "urban_introspective"
    if classical_hits > 0:
        return "classical_restraint"
    return ""


def _infer_profile_confidence_from_source_ids(source_ids: list[str], profile_vote: str) -> float:
    if not source_ids or not profile_vote:
        return 0.0
    total = len(source_ids)
    if profile_vote == "urban_introspective":
        hits = sum(1 for x in source_ids if x.startswith("lyric-modern-"))
        return hits / max(total, 1)
    if profile_vote == "classical_restraint":
        hits = sum(1 for x in source_ids if x.startswith("poem-"))
        return hits / max(total, 1)
    return 0.0


def _ensure_retrieval_profile_decision(trace: dict[str, object]) -> dict[str, object]:
    existing_decision = trace.get("retrieval_profile_decision")
    if isinstance(existing_decision, dict):
        profile_vote = str(existing_decision.get("profile_vote", "")).strip()
        vote_confidence = _safe_float(existing_decision.get("vote_confidence", 0.0), default=0.0)
        active_profile = str(existing_decision.get("active_profile", "")).strip()
        decision_reason = str(existing_decision.get("decision_reason", "")).strip()
        source_ids_raw = existing_decision.get("source_ids", trace.get("few_shot_source_ids", []))
        source_ids = [str(x) for x in source_ids_raw] if isinstance(source_ids_raw, list) else []
        source_stage = str(existing_decision.get("source_stage", trace.get("retrieval_profile_source", "initial"))).strip() or "initial"

        if (not profile_vote) or (not active_profile):
            inferred_vote = _infer_profile_vote_from_source_ids(source_ids)
            inferred_confidence = _infer_profile_confidence_from_source_ids(source_ids, inferred_vote)
            if inferred_vote:
                profile_vote = inferred_vote
                vote_confidence = max(vote_confidence, inferred_confidence)
                active_profile = inferred_vote if vote_confidence >= (2 / 3) else ""
                if active_profile:
                    decision_reason = "activated"
                elif not decision_reason:
                    decision_reason = "insufficient_confidence"

            trace["retrieval_profile_decision"] = {
                "profile_vote": profile_vote,
                "vote_confidence": vote_confidence,
                "active_profile": active_profile,
                "decision_reason": decision_reason or "no_profile_vote",
                "source_stage": source_stage,
                "source_ids": source_ids,
            }
        return trace

    profile_vote = str(trace.get("retrieval_profile_vote", "")).strip()
    vote_confidence = _safe_float(trace.get("retrieval_vote_confidence", 0.0), default=0.0)
    source_ids_raw = trace.get("few_shot_source_ids", [])
    source_ids = [str(x) for x in source_ids_raw] if isinstance(source_ids_raw, list) else []
    source_stage = str(trace.get("retrieval_profile_source", "initial")).strip() or "initial"

    if not profile_vote:
        profile_vote = _infer_profile_vote_from_source_ids(source_ids)
        vote_confidence = _infer_profile_confidence_from_source_ids(source_ids, profile_vote)

    has_vote = bool(profile_vote)
    confidence_ok = vote_confidence >= (2 / 3)
    active_profile = profile_vote if (has_vote and confidence_ok) else ""
    if active_profile:
        decision_reason = "activated"
    elif not has_vote:
        decision_reason = "no_profile_vote"
    else:
        decision_reason = "insufficient_confidence"

    trace["retrieval_profile_decision"] = {
        "profile_vote": profile_vote,
        "vote_confidence": vote_confidence,
        "active_profile": active_profile,
        "decision_reason": decision_reason,
        "source_stage": source_stage,
        "source_ids": source_ids,
    }
    return trace


def _format_lyrics(payload: LyricPayload) -> str:
    lines: list[str] = []
    for section in payload.lyrics_by_section:
        lines.append(section.tag)
        for row in section.lines:
            main = row.primary.strip()
            backing = row.backing.strip()
            if backing:
                lines.append(f"{main} ({backing})")
            else:
                lines.append(main)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _format_style(payload: LyricPayload) -> str:
    tags: list[str] = []
    tags.extend(payload.style_tags.genre)
    tags.extend(payload.style_tags.mood)
    tags.extend(payload.style_tags.instruments)
    tags.extend(payload.style_tags.vocals)
    tags.extend(payload.style_tags.production)
    unique = []
    for tag in tags:
        t = tag.strip()
        if t and t not in unique:
            unique.append(t)
    return ", ".join(unique[:8]) + "\n"


def _format_exclude(payload: LyricPayload) -> str:
    unique = []
    for tag in payload.exclude_tags:
        t = tag.strip()
        if t and t not in unique:
            unique.append(t)
    return "(" + ", ".join(unique) + ")\n" if unique else "\n"


def _load_profile_display_name(out_dir: Path, profile_id: str) -> str:
    if not profile_id:
        return ""
    registry_path = out_dir.parent / "src" / "profiles" / "registry.json"
    if not registry_path.exists():
        return ""
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        return ""
    profile = profiles.get(profile_id, {})
    if not isinstance(profile, dict):
        return ""
    return str(profile.get("display_name", "")).strip()


def _format_audit_md(out_dir: Path, trace: dict[str, Any]) -> str:
    active_profile = str(trace.get("active_profile", "")).strip()
    display_name = _load_profile_display_name(out_dir, active_profile)
    profile_source = str(trace.get("profile_source", "")).strip()
    vote_confidence = trace.get("profile_vote_confidence", trace.get("retrieval_vote_confidence", None))
    vote_counts_raw = trace.get("retrieval_profile_vote_counts", {})
    if isinstance(vote_counts_raw, dict):
        vote_counts = {str(k): int(v) for k, v in vote_counts_raw.items()}
    else:
        vote_counts = {}
    vote_counts_line = (
        ", ".join(f"{k}:{v}" for k, v in sorted(vote_counts.items(), key=lambda x: x[0]))
        if vote_counts
        else "(none)"
    )
    profile_warnings_raw = trace.get("profile_routing_warnings", [])
    profile_warnings = (
        [str(x) for x in profile_warnings_raw if str(x).strip()]
        if isinstance(profile_warnings_raw, list)
        else []
    )

    lint_report = trace.get("lint_report", {})
    skipped = []
    if isinstance(lint_report, dict):
        raw = lint_report.get("skipped_rules_by_profile", [])
        if isinstance(raw, list):
            skipped = [str(x) for x in raw if str(x).strip()]

    lines = [
        "# audit.md",
        "",
        "## 0. Profile 决策",
        f"- active_profile: {active_profile}",
        f"- display_name: {display_name}",
        f"- profile_source: {profile_source}",
        f"- vote_confidence: {vote_confidence}",
        f"- profile_vote_counts: {vote_counts_line}",
        f"- warnings: {'; '.join(profile_warnings) if profile_warnings else '(none)'}",
        f"- skipped_rules_by_profile: {', '.join(skipped) if skipped else '(none)'}",
    ]

    few_shot_rows = trace.get("few_shot_examples", [])
    lines.extend(["", "## 1. Few-shot 来源透明化"])
    if isinstance(few_shot_rows, list) and few_shot_rows:
        for item in few_shot_rows:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id", "")).strip()
            content_preview = str(item.get("content_preview", "")).strip()
            learn_point = str(item.get("learn_point", "")).strip()
            do_not_copy = str(item.get("do_not_copy", "")).strip()
            lines.append(
                f"- source_id={source_id} | content_preview={content_preview} | learn_point={learn_point} | do_not_copy={do_not_copy}"
            )
    else:
        lines.append("- (none)")

    lines.extend(["", "## 2. Lint 概览", "- (pending)", "", "## 3. 产物状态", "- (pending)", "", "## 4. 运行结论", "- (pending)"])
    return "\n".join(lines).strip() + "\n"


def write_outputs(payload: LyricPayload, out_dir: Path, trace: dict[str, object]) -> None:
    verse_count, chorus_count = _count_required_sections(payload)
    trace.setdefault("compile_structure", {})
    if isinstance(trace.get("compile_structure"), dict):
        trace["compile_structure"]["verse_sections"] = verse_count
        trace["compile_structure"]["chorus_sections"] = chorus_count
        trace["compile_structure"]["structural_ready"] = verse_count >= 1 and chorus_count >= 1
    _validate_required_sections(payload)
    out_dir.mkdir(parents=True, exist_ok=True)
    trace = _ensure_retrieval_profile_decision(dict(trace))
    (out_dir / "lyrics.txt").write_text(_format_lyrics(payload), encoding="utf-8")
    (out_dir / "style.txt").write_text(_format_style(payload), encoding="utf-8")
    (out_dir / "exclude.txt").write_text(_format_exclude(payload), encoding="utf-8")
    (out_dir / "lyric_payload.json").write_text(
        payload.model_dump_json(indent=2), encoding="utf-8"
    )
    (out_dir / "trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "audit.md").write_text(_format_audit_md(out_dir, trace), encoding="utf-8")


def write_trace_and_audit(out_dir: Path, trace: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    normalized = _ensure_retrieval_profile_decision(dict(trace))
    (out_dir / "trace.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "audit.md").write_text(_format_audit_md(out_dir, normalized), encoding="utf-8")
