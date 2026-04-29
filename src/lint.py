from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
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
    "[Beat Break]",
    "(Pause)",
    "(Breathe)",
    "(...)",
}

OPEN_FINALS = {"a", "ang", "ai", "ao", "ou"}
# Include tone 0/5 (neutral/light tone) so modal particles like 啊/呀/哦/嘛 are accepted
OPEN_TONES = {"1", "2", "0", "5"}

ROOT_DIR = Path(__file__).resolve().parents[1]
PROFILES_REGISTRY_PATH = ROOT_DIR / "src" / "profiles" / "registry.json"
PROFILES_GLOBAL_RULES_PATH = ROOT_DIR / "src" / "profiles" / "global_rules.json"


@dataclass
class Violation:
    rule: str
    detail: str
    section: str = ""
    line: int = 0


class RuleSeverity(str, Enum):
    HARD_KILL = "HARD_KILL"
    HARD_PENALTY = "HARD_PENALTY"
    SOFT_PENALTY = "SOFT_PENALTY"


RULE_DEFINITIONS: dict[str, RuleSeverity] = {
    "R01": RuleSeverity.SOFT_PENALTY,  # downgraded: proxy metric, should not single-handedly kill craft score
    "R02": RuleSeverity.SOFT_PENALTY,
    "R03": RuleSeverity.HARD_KILL,
    "R05": RuleSeverity.SOFT_PENALTY,
    "R06": RuleSeverity.SOFT_PENALTY,
    "R14": RuleSeverity.SOFT_PENALTY,  # downgraded: 3 hardcoded phrases are too brittle for HARD_KILL
    "R15": RuleSeverity.HARD_PENALTY,
    "R16_global": RuleSeverity.HARD_KILL,
    "R16_profile": RuleSeverity.HARD_PENALTY,
    "R17": RuleSeverity.SOFT_PENALTY,
    "R18": RuleSeverity.HARD_PENALTY,
}

RULE_WEIGHTS: dict[str, int] = {
    "R01": 8,
    "R02": 4,
    "R03": 10,
    "R05": 4,
    "R06": 3,
    "R14": 10,
    "R15": 5,
    "R16_global": 10,
    "R16_profile": 5,
    "R17": 3,
    "R18": 5,
}

R14_FORBIDDEN_PHRASES = [
    "折成静默",
    "浇浅",
    "收回来",
]


def _violation_rule_key(v: Violation) -> str:
    if v.rule != "R16":
        return v.rule
    if "(global)" in v.detail:
        return "R16_global"
    return "R16_profile"


def evaluate_violation_severity(violations: list[Violation]) -> dict[str, Any]:
    hard_kill: list[str] = []
    hard_penalty = 0
    soft_penalty = 0
    death_reason: list[str] = []

    for violation in violations:
        key = _violation_rule_key(violation)
        severity = RULE_DEFINITIONS.get(key, RuleSeverity.SOFT_PENALTY)
        if severity == RuleSeverity.HARD_KILL:
            hard_kill.append(key)
            death_reason.append(f"{key}: {violation.detail}")
        elif severity == RuleSeverity.HARD_PENALTY:
            hard_penalty += 1
        else:
            soft_penalty += 1

    is_dead = bool(hard_kill)
    penalty_score = hard_penalty * 5 + soft_penalty
    return {
        "is_dead": is_dead,
        "hard_kill_rules": sorted(set(hard_kill)),
        "hard_penalty_count": hard_penalty,
        "soft_penalty_count": soft_penalty,
        "penalty_score": penalty_score,
        "death_reason": death_reason,
    }


def calculate_craft_score(violations: list[Violation]) -> float:
    failed_weights = 0
    total_weights = sum(RULE_WEIGHTS.values())
    failed_keys: set[str] = set()
    for violation in violations:
        key = _violation_rule_key(violation)
        if key in failed_keys:
            continue
        failed_keys.add(key)
        failed_weights += RULE_WEIGHTS.get(key, 1)
    passed_weights = max(total_weights - failed_weights, 0)
    return passed_weights / total_weights if total_weights else 0.0


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

    # R14 hard kill phrase check (动宾合法性)
    for section, idx, line in rows:
        for phrase in R14_FORBIDDEN_PHRASES:
            if phrase in line:
                violations.append(
                    Violation(
                        rule="R14",
                        detail=f"forbidden verb-object phrase: {phrase}",
                        section=section,
                        line=idx,
                    )
                )

    # R01 chorus hook line tail (zh-CN)
    # Skipped for profiles that use oblique-tone rhyme schemes (e.g. classical_restraint)
    skip_r01 = bool(profile_cfg.get("skip_R01", False)) if isinstance(profile_cfg, dict) else False
    if skip_r01:
        skipped_rules_by_profile.append("R01")
    hook_section = payload.structure.hook_section
    hook_idx = payload.structure.hook_line_index
    if not skip_r01:
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

    # R05 per-section line-length +/-3 around mean, with short-line exemption
    # Lines of <=5 chars are treated as intentional "breath-pause" lines (urban profile rhythm
    # calls for short-punch + long-flow cadence) and are excluded from the mean calculation.
    SHORT_LINE_EXEMPT = 5
    TOLERANCE = 3
    for section in payload.lyrics_by_section:
        all_lengths = [(idx, len(line.primary.strip())) for idx, line in enumerate(section.lines, start=1) if line.primary.strip()]
        non_short = [sz for _, sz in all_lengths if sz > SHORT_LINE_EXEMPT]
        if not non_short:
            continue
        mean_len = sum(non_short) / len(non_short)
        for idx, line in enumerate(section.lines, start=1):
            size = len(line.primary.strip())
            if size == 0:
                continue
            if size <= SHORT_LINE_EXEMPT:
                continue  # intentional short line, exempt from mean-based tolerance
            if abs(size - mean_len) > TOLERANCE:
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

    # R18 section-level rhythm contract (HARD_PENALTY)
    # 1) line-length span within each section must be <= 2
    # 2) when touching lower/upper line boundary, required metatags must exist
    _SECTION_TAG_TO_KEYS: dict[str, tuple[str, str]] = {
        "[Verse]": ("verse_line_min", "verse_line_max"),
        "[Verse 1]": ("verse_line_min", "verse_line_max"),
        "[Verse 2]": ("verse_line_min", "verse_line_max"),
        "[Pre-Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Final Chorus]": ("chorus_line_min", "chorus_line_max"),
        "[Bridge]": ("bridge_line_min", "bridge_line_max"),
        "[Outro]": ("bridge_line_min", "bridge_line_max"),
    }
    _SPAN_LIMIT = 2
    _LOWER_TAGS = {"(Pause)", "(Breathe)"}
    _UPPER_TAGS = {"[Fast Flow]"}

    def _bare_len(raw: str) -> int:
        text = raw.strip()
        return len("".join(c for c in text if c.strip() and c not in "，。？！、；：""''《》【】…—～·"))

    if isinstance(trace, dict):
        prosody = trace.get("prosody_contract", {})
        if isinstance(prosody, dict):
            for section in payload.lyrics_by_section:
                key_pair = _SECTION_TAG_TO_KEYS.get(section.tag)
                if key_pair is None:
                    continue
                lower_key, upper_key = key_pair
                line_min = prosody.get(lower_key)
                line_max = prosody.get(upper_key)
                if line_min is None or line_max is None:
                    continue

                line_lengths: list[tuple[int, int, str]] = []
                for idx, line in enumerate(section.lines, start=1):
                    text = line.primary.strip()
                    if not text:
                        continue
                    line_lengths.append((idx, _bare_len(text), text))
                if not line_lengths:
                    continue

                min_len = min(x[1] for x in line_lengths)
                max_len = max(x[1] for x in line_lengths)
                if (max_len - min_len) > _SPAN_LIMIT:
                    violations.append(
                        Violation(
                            rule="R18",
                            detail=f"line span exceeds 2 in {section.tag}: min={min_len}, max={max_len}",
                            section=section.tag,
                            line=0,
                        )
                    )

                inline_tags = {str(t).strip() for t in section.voice_tags_inline if str(t).strip()}
                for idx, bare_len, text in line_lengths:
                    if bare_len <= int(line_min) and not (inline_tags & _LOWER_TAGS):
                        violations.append(
                            Violation(
                                rule="R18",
                                detail=(
                                    f"missing required metatag for lower-bound line in {section.tag} line {idx}: "
                                    f"len={bare_len}, min={line_min}, require one of {sorted(_LOWER_TAGS)}"
                                ),
                                section=section.tag,
                                line=idx,
                            )
                        )
                    if bare_len >= int(line_max) and not (inline_tags & _UPPER_TAGS):
                        violations.append(
                            Violation(
                                rule="R18",
                                detail=(
                                    f"missing required metatag for upper-bound line in {section.tag} line {idx}: "
                                    f"len={bare_len}, max={line_max}, require one of {sorted(_UPPER_TAGS)}"
                                ),
                                section=section.tag,
                                line=idx,
                            )
                        )

    failed_rules = sorted({v.rule for v in violations})
    severity = evaluate_violation_severity(violations)
    craft_score = calculate_craft_score(violations)
    return {
        "pass": len(violations) == 0 and not severity["is_dead"],
        "failed_rules": failed_rules,
        "violations": [v.__dict__ for v in violations],
        "active_profile": active_profile,
        "skipped_rules_by_profile": skipped_rules_by_profile,
        "profile_specific_violations": profile_specific_violations,
        "is_dead": severity["is_dead"],
        "death_reason": severity["death_reason"],
        "hard_kill_rules": severity["hard_kill_rules"],
        "hard_penalty_count": severity["hard_penalty_count"],
        "soft_penalty_count": severity["soft_penalty_count"],
        "penalty_score": severity["penalty_score"],
        "craft_score": craft_score,
        "all_dead_run_status": "",
    }
