from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import jieba
from pypinyin import Style, pinyin
from rapidfuzz import fuzz

from src.schemas import LyricPayload


TAG_WHITELIST = {
    "[Intro]",
    "[Verse]",
    "[Verse 1]",
    "[Verse 2]",
    "[Pre-Chorus]",
    "[Chorus]",
    "[Post-Chorus]",
    "[Bridge]",
    "[Outro]",
    "[Hook]",
    "[Drop]",
    "[Build-up]",
    "[Breakdown]",
    "[Instrumental]",
    "[Final Chorus]",
}

OPEN_FINALS = {"a", "ang", "ai", "ao", "ou"}
OPEN_TONES = {"1", "2"}


@dataclass
class Violation:
    rule: str
    detail: str
    section: str = ""
    line: int = 0


def _all_lines(payload: LyricPayload) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for section in payload.lyrics_by_section:
        for idx, line in enumerate(section.lines, start=1):
            rows.append((section.tag, idx, line.primary.strip()))
    return rows


def _line_tail_ok_zh(text: str) -> bool:
    if not text:
        return False
    tail = text[-1]
    finals = pinyin(tail, style=Style.FINALS, strict=False)
    tones = pinyin(tail, style=Style.TONE3, strict=False)
    if not finals or not tones:
        return False
    final = finals[0][0].lower().strip()
    tone = tones[0][0][-1] if tones[0][0] and tones[0][0][-1].isdigit() else ""
    return final in OPEN_FINALS and tone in OPEN_TONES


def lint_payload(payload: LyricPayload) -> dict[str, Any]:
    violations: list[Violation] = []
    rows = _all_lines(payload)

    if not rows:
        violations.append(Violation(rule="R00", detail="lyrics_by_section is empty"))
        return {
            "pass": False,
            "failed_rules": ["R00"],
            "violations": [v.__dict__ for v in violations],
        }

    # R06 tag whitelist
    for section in payload.lyrics_by_section:
        if section.tag not in TAG_WHITELIST:
            violations.append(
                Violation(rule="R06", detail=f"tag not in whitelist: {section.tag}")
            )

    # R03 forbidden literal phrases (fuzzy threshold 92)
    text_lines = [x[2] for x in rows if x[2]]
    forbidden = [x.strip() for x in payload.distillation.forbidden_literal_phrases if x.strip()]
    for phrase in forbidden:
        for section, idx, line in rows:
            if line and fuzz.partial_ratio(phrase, line) >= 92:
                violations.append(
                    Violation(
                        rule="R03",
                        detail=f"forbidden literal phrase hit: {phrase}",
                        section=section,
                        line=idx,
                    )
                )

    # R01 chorus hook line tail (zh-CN)
    hook_section = payload.structure.hook_section
    hook_idx = payload.structure.hook_line_index
    for section in payload.lyrics_by_section:
        if section.tag != hook_section:
            continue
        if 1 <= hook_idx <= len(section.lines):
            line_text = section.lines[hook_idx - 1].primary.strip()
            if not _line_tail_ok_zh(line_text):
                violations.append(
                    Violation(
                        rule="R01",
                        detail="hook line tail is not open-final with level tone",
                        section=section.tag,
                        line=hook_idx,
                    )
                )
        else:
            violations.append(
                Violation(
                    rule="R01",
                    detail="hook_line_index out of range",
                    section=section.tag,
                    line=hook_idx,
                )
            )

    # R02 concrete noun overuse <= 3
    tokens: list[str] = []
    for line in text_lines:
        for token in jieba.lcut(line):
            w = token.strip()
            if len(w) >= 2:
                tokens.append(w)
    counts = Counter(tokens)
    for token, count in counts.items():
        if count > 3:
            violations.append(
                Violation(rule="R02", detail=f"token overused: {token} x{count}")
            )

    # R05 per-section line-length +/-2 around mean
    for section in payload.lyrics_by_section:
        lengths = [len(line.primary.strip()) for line in section.lines if line.primary.strip()]
        if not lengths:
            continue
        mean_len = sum(lengths) / len(lengths)
        for idx, line in enumerate(section.lines, start=1):
            size = len(line.primary.strip())
            if abs(size - mean_len) > 2:
                violations.append(
                    Violation(
                        rule="R05",
                        detail=f"line length out of tolerance: {size} vs mean {mean_len:.1f}",
                        section=section.tag,
                        line=idx,
                    )
                )

    failed_rules = sorted({v.rule for v in violations})
    return {
        "pass": len(violations) == 0,
        "failed_rules": failed_rules,
        "violations": [v.__dict__ for v in violations],
    }
