from __future__ import annotations

import json
from pathlib import Path

from src.schemas import LyricPayload


def _safe_float(value: object, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ensure_retrieval_profile_decision(trace: dict[str, object]) -> dict[str, object]:
    if isinstance(trace.get("retrieval_profile_decision"), dict):
        return trace

    profile_vote = str(trace.get("retrieval_profile_vote", "")).strip()
    vote_confidence = _safe_float(trace.get("retrieval_vote_confidence", 0.0), default=0.0)
    source_ids_raw = trace.get("few_shot_source_ids", [])
    source_ids = [str(x) for x in source_ids_raw] if isinstance(source_ids_raw, list) else []
    source_stage = str(trace.get("retrieval_profile_source", "initial")).strip() or "initial"

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
