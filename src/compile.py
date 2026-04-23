from __future__ import annotations

import json
from pathlib import Path

from src.schemas import LyricPayload


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


def write_outputs(payload: LyricPayload, out_dir: Path, trace: dict[str, object]) -> None:
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
