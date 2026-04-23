from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
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

ROOT_DIR = Path(__file__).resolve().parents[1]
PROFILES_REGISTRY_PATH = ROOT_DIR / "src" / "profiles" / "registry.json"
PROFILES_GLOBAL_RULES_PATH = ROOT_DIR / "src" / "profiles" / "global_rules.json"


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


def _load_profiles_registry(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    return {str(k): v for k, v in profiles.items() if isinstance(v, dict)}


def _load_global_forbidden(path: Path) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("global_always_forbidden", [])
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _get_active_profile(trace: dict[str, Any] | None, profiles: dict[str, dict[str, Any]]) -> str:
    if not isinstance(trace, dict):
        return ""
    active = str(trace.get("active_profile", "")).strip()
    if active in profiles:
        return active
    decision = trace.get("retrieval_profile_decision", {})
    if isinstance(decision, dict):
        active = str(decision.get("active_profile", "")).strip()
        if active in profiles:
            return active
    return ""


def _concrete_density(lines: list[str]) -> float:
    if not lines:
        return 0.0
    concrete = 0
    for line in lines:
        concrete += sum(1 for token in jieba.lcut(line) if len(token.strip()) >= 2)
    return concrete / max(len(lines), 1)


def _first_person_ratio(lines: list[str]) -> float:
    chars = "".join(lines)
    if not chars:
        return 0.0
    first_person_hits = chars.count("我")
    return first_person_hits / max(len(chars), 1)


def lint_payload(
    payload: LyricPayload,
    *,
    trace: dict[str, Any] | None = None,
    profiles_registry_path: Path = PROFILES_REGISTRY_PATH,
    global_rules_path: Path = PROFILES_GLOBAL_RULES_PATH,
) -> dict[str, Any]:
    violations: list[Violation] = []
    rows = _all_lines(payload)
    profiles = _load_profiles_registry(profiles_registry_path)
    global_forbidden = _load_global_forbidden(global_rules_path)

    active_profile = _get_active_profile(trace, profiles)
    profile_cfg = profiles.get(active_profile, {}) if active_profile else {}
    skipped_rules_by_profile: list[str] = []
    profile_specific_violations: list[dict[str, Any]] = []

    if not rows:
        violations.append(Violation(rule="R00", detail="lyrics_by_section is empty"))
        return {
            "pass": False,
            "failed_rules": ["R00"],
            "violations": [v.__dict__ for v in violations],
            "active_profile": active_profile,
            "skipped_rules_by_profile": skipped_rules_by_profile,
            "profile_specific_violations": profile_specific_violations,
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

    # R15 profile concrete-density policy
    r15_cfg = profile_cfg.get("R15_concrete_density", {}) if isinstance(profile_cfg, dict) else {}
    if isinstance(r15_cfg, dict) and not bool(r15_cfg.get("enforced", True)):
        skipped_rules_by_profile.append("R15")
    elif isinstance(r15_cfg, dict):
        density = _concrete_density(text_lines)
        direction = str(r15_cfg.get("direction", "lower_bound"))
        if direction == "upper_bound":
            verse_max = float(r15_cfg.get("verse_max", 999.0))
            if density > verse_max:
                violations.append(Violation(rule="R15", detail=f"concrete density {density:.2f} exceeds upper bound {verse_max:.2f}"))
        else:
            verse_min = float(r15_cfg.get("verse_min", 0.0))
            if density < verse_min:
                violations.append(Violation(rule="R15", detail=f"concrete density {density:.2f} below lower bound {verse_min:.2f}"))

    # R16 merged blacklist (global + profile)
    profile_forbidden = profile_cfg.get("R16_profile_forbidden", []) if isinstance(profile_cfg, dict) else []
    profile_forbidden_list = [str(x).strip() for x in profile_forbidden if str(x).strip()] if isinstance(profile_forbidden, list) else []
    merged = []
    for phrase in [*global_forbidden, *profile_forbidden_list]:
        if phrase and phrase not in merged:
            merged.append(phrase)
    for section, idx, line in rows:
        for phrase in merged:
            if phrase and phrase in line:
                source = "global" if phrase in global_forbidden else "profile"
                violations.append(
                    Violation(
                        rule="R16",
                        detail=f"forbidden phrase hit ({source}): {phrase}",
                        section=section,
                        line=idx,
                    )
                )
                profile_specific_violations.append(
                    {
                        "rule": "R16",
                        "source": source,
                        "phrase": phrase,
                        "section": section,
                        "line": idx,
                    }
                )

    # R17 first-person ratio by profile
    max_ratio = profile_cfg.get("R17_first_person_ratio_max") if isinstance(profile_cfg, dict) else None
    if isinstance(max_ratio, (int, float)):
        ratio = _first_person_ratio(text_lines)
        if ratio > float(max_ratio):
            violations.append(Violation(rule="R17", detail=f"first-person ratio {ratio:.3f} exceeds max {float(max_ratio):.3f}"))

    failed_rules = sorted({v.rule for v in violations})
    return {
        "pass": len(violations) == 0,
        "failed_rules": failed_rules,
        "violations": [v.__dict__ for v in violations],
        "active_profile": active_profile,
        "skipped_rules_by_profile": skipped_rules_by_profile,
        "profile_specific_violations": profile_specific_violations,
    }
