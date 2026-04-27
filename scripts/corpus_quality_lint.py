from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz


_DIGIT_3_RE = re.compile(r"\d{3,}")
_CN_DIGIT_3_RE = re.compile(r"[零〇一二三四五六七八九十百千万两壹贰叁肆伍陆柒捌玖拾佰仟]{3,}")
_BAD_WORD_RE = re.compile(r"placeholder|todo|test|示例|sample", re.IGNORECASE)
_CN_RE = re.compile(r"[\u4e00-\u9fff]")
_GARBLED_RE = re.compile(r"�|\ufffd|��")

_IDIOM_MAX_LEN = 8
_MODERN_R16_BLACKLIST = {
    "学会放下",
    "慢慢放下",
    "默默走远",
    "各自安好",
    "回到原点",
    "回原点",
    "归零",
    "归位",
    "应停的位置",
    "该在的位置",
    "慢慢习惯",
    "终究会习惯",
}

_VERB_CHARS = {
    "是",
    "有",
    "在",
    "走",
    "看",
    "听",
    "想",
    "爱",
    "写",
    "唱",
    "说",
    "等",
    "把",
    "让",
    "给",
    "留",
    "落",
    "归",
    "去",
    "来",
    "停",
    "放",
    "收",
    "开",
    "过",
    "跳",
    "舞",
    "摇",
    "推",
    "撞",
    "燃",
    "追",
    "拥",
    "抱",
}


@dataclass
class RowLintReport:
    passed: bool
    failed_rules: list[str]
    reasons: list[str]


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _contains_chinese_digits(text: str) -> bool:
    return bool(_DIGIT_3_RE.search(text) or _CN_DIGIT_3_RE.search(text))


def _verb_ratio(text: str) -> float:
    chars = [ch for ch in text if _CN_RE.match(ch)]
    if not chars:
        return 1.0
    verbs = sum(1 for ch in chars if ch in _VERB_CHARS)
    return verbs / len(chars)


def _is_idiom_row(row: dict[str, Any]) -> bool:
    source_family = _string(row.get("source_family")).lower()
    source_id = _string(row.get("source_id")).lower()
    return source_family == "chengyu" or source_id.startswith("idiom:")


def _contains_modern_blacklist(text: str) -> bool:
    return any(phrase in text for phrase in _MODERN_R16_BLACKLIST)


def lint_corpus_row(row: dict[str, Any], *, mode: str = "ingestion") -> RowLintReport:
    failed: list[str] = []
    reasons: list[str] = []

    content = _string(row.get("content"))
    learn_point = _string(row.get("learn_point"))
    do_not_copy = _string(row.get("do_not_copy"))
    emotion_tags = row.get("emotion_tags")
    profile_tag = _string(row.get("profile_tag"))
    valence = _string(row.get("valence"))
    row_type = _string(row.get("type")).lower()

    joined_text = " ".join([content, learn_point])

    # Classical poems often use numbers as literary device; exempt them
    if row_type != "classical_poem" and _contains_chinese_digits(content):
        failed.append("RULE_C1")
        reasons.append("content contains >=3 consecutive digits")

    length = len(content)
    if _is_idiom_row(row):
        if length < 2 or length > 800:
            failed.append("RULE_C3")
            reasons.append(f"content length out of range: {length}")
    else:
        if length < 10 or length > 800:
            failed.append("RULE_C3")
            reasons.append(f"content length out of range: {length}")

    missing_profile_tag = (not profile_tag)
    missing_valence = (not valence)
    if not isinstance(emotion_tags, list) or not emotion_tags or missing_profile_tag or missing_valence:
        failed.append("RULE_C4")
        reasons.append("missing emotion_tags/profile_tag/valence")

    if not learn_point or len(learn_point) < 5:
        failed.append("RULE_C5")
        reasons.append("learn_point missing or too short")

    # Classical poems don't need do_not_copy
    if row_type != "classical_poem" and not do_not_copy:
        failed.append("RULE_C8")
        reasons.append("do_not_copy missing")

    # Classical v2 enrichment checks
    if row_type == "classical_poem":
        if not _string(row.get("emotion_core")):
            failed.append("RULE_C11")
            reasons.append("classical poem missing emotion_core")
        if not _string(row.get("archetype")):
            failed.append("RULE_C12")
            reasons.append("classical poem missing archetype")
        if not row.get("phonetic_rhythm"):
            failed.append("RULE_C13")
            reasons.append("classical poem missing phonetic_rhythm")

    if _BAD_WORD_RE.search(joined_text):
        failed.append("RULE_C6")
        reasons.append("placeholder/test marker detected")

    # Classical poems often have low verb ratios; exempt them
    if row_type != "classical_poem" and _verb_ratio(content) < 0.10:
        failed.append("RULE_C7")
        reasons.append("verb ratio below 10%")

    if _is_idiom_row(row):
        idiom_text = _string(row.get("content") or row.get("title"))
        if len(idiom_text) > _IDIOM_MAX_LEN:
            failed.append("RULE_C9")
            reasons.append(f"idiom length exceeds max {_IDIOM_MAX_LEN}: {len(idiom_text)}")

        if _GARBLED_RE.search(idiom_text):
            failed.append("RULE_C10")
            reasons.append("idiom text contains garbled characters")

    if row_type == "modern_lyric" and _contains_modern_blacklist(content):
        failed.append("RULE_R16_MODERN")
        reasons.append("modern lyric hits R16 modern blacklist")

    return RowLintReport(passed=not failed, failed_rules=failed, reasons=reasons)


def dedupe_similar_rows(rows: list[dict[str, Any]], *, threshold: int = 80) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for row in rows:
        key = (_string(row.get("title")), _string(row.get("profile_tag")))
        grouped.setdefault(key, []).append(row)

    for _, group_rows in grouped.items():
        for row in group_rows:
            content = _string(row.get("content"))
            duplicate = False
            for existing in kept:
                same_title = _string(existing.get("title")) == _string(row.get("title"))
                same_profile = _string(existing.get("profile_tag")) == _string(row.get("profile_tag"))
                if not (same_title and same_profile):
                    continue
                score = fuzz.ratio(content, _string(existing.get("content")))
                if score >= threshold:
                    duplicate = True
                    break
            if duplicate:
                row = dict(row)
                row["_rejected_rules"] = ["RULE_C2"]
                row["_rejected_reasons"] = ["high similarity with same title/profile"]
                dropped.append(row)
            else:
                kept.append(row)

    return kept, dropped
