from __future__ import annotations

import json
from pathlib import Path

from src.schemas import LyricPayload


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
    (out_dir / "lyrics.txt").write_text(_format_lyrics(payload), encoding="utf-8")
    (out_dir / "style.txt").write_text(_format_style(payload), encoding="utf-8")
    (out_dir / "exclude.txt").write_text(_format_exclude(payload), encoding="utf-8")
    (out_dir / "lyric_payload.json").write_text(
        payload.model_dump_json(indent=2), encoding="utf-8"
    )
    (out_dir / "trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
