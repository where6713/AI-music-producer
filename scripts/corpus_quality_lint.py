from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz


_DIGIT_3_RE = re.compile(r"\d{3,}")
_BAD_WORD_RE = re.compile(r"placeholder|todo|test|示例|sample", re.IGNORECASE)
_CN_RE = re.compile(r"[\u4e00-\u9fff]")

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
    if not _CN_RE.search(text):
        return False
    return bool(_DIGIT_3_RE.search(text))


def _verb_ratio(text: str) -> float:
    chars = [ch for ch in text if _CN_RE.match(ch)]
    if not chars:
        return 1.0
    verbs = sum(1 for ch in chars if ch in _VERB_CHARS)
    return verbs / len(chars)


def lint_corpus_row(row: dict[str, Any], *, mode: str = "ingestion") -> RowLintReport:
    failed: list[str] = []
    reasons: list[str] = []

    content = _string(row.get("content"))
    learn_point = _string(row.get("learn_point"))
    emotion_tags = row.get("emotion_tags")
    profile_tag = _string(row.get("profile_tag"))
    valence = _string(row.get("valence"))

    joined_text = " ".join([content, learn_point])

    if _contains_chinese_digits(content):
        failed.append("RULE_C1")
        reasons.append("content contains >=3 consecutive digits")

    length = len(content)
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

    if _BAD_WORD_RE.search(joined_text):
        failed.append("RULE_C6")
        reasons.append("placeholder/test marker detected")

    if _verb_ratio(content) < 0.10:
        failed.append("RULE_C7")
        reasons.append("verb ratio below 10%")

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
