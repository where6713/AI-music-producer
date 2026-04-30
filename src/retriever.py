from __future__ import annotations

import json
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.corpus_quality_lint import lint_corpus_row
from src.schemas import UserInput


CORPUS_FILES = [
    "corpus/poetry_classical.json",
    "corpus/lyrics_modern_zh.json",
]

CLEAN_CORPUS_FILES = [
    "corpus/_clean/poetry_classical.json",
    "corpus/_clean/lyrics_modern_zh.json",
]

# Golden anchor files: curated high-quality lyricist examples (林夕 etc.)
# These bypass runtime lint — they are pre-validated golden references.
GOLDEN_ANCHOR_FILES = [
    "corpus/_raw/golden_anchors_modern_llm_enriched.json",
    "corpus/_raw/golden_anchors_classical.json",
]

PROFILE_IDS = {
    "urban_introspective",
    "classical_restraint",
    "uplift_pop",
    "club_dance",
    "ambient_meditation",
}

MIN_PROFILE_COVERAGE = {
    "urban_introspective": 200,
    "classical_restraint": 200,
    "uplift_pop": 150,
    "club_dance": 100,
    "ambient_meditation": 80,
}


class InsufficientQualityFewShotError(RuntimeError):
    pass


def _infer_profile_tag(row: dict[str, Any]) -> str:
    explicit = str(row.get("profile_tag", "")).strip()
    if explicit:
        return explicit

    row_type = str(row.get("type", "")).strip().lower()
    tags = [str(x).strip().lower() for x in row.get("emotion_tags", []) if str(x).strip()]

    if row_type == "modern_lyric":
        if any(x in tags for x in {"breakup", "late-night", "regret", "distance", "self-control"}):
            return "urban_introspective"
        return "urban_introspective"

    if row_type == "classical_poem":
        if any(x in tags for x in {"restraint", "nostalgia", "longing", "night", "separation"}):
            return "classical_restraint"
        return "classical_restraint"

    return ""


def _tokenize(text: str) -> list[str]:
    val = text.strip().lower()
    if not val:
        return []
    if any("\u4e00" <= ch <= "\u9fff" for ch in val):
        return [ch for ch in val if "\u4e00" <= ch <= "\u9fff"]
    return [x for x in val.replace(",", " ").replace(".", " ").split() if x]


def _load_corpus(repo_root: Path) -> list[dict[str, Any]]:
    has_clean = all((repo_root / rel).exists() for rel in CLEAN_CORPUS_FILES)
    if not has_clean:
        raise RuntimeError("clean corpus missing: run scripts/run_corpus_ingestion.py --strict")

    rows: list[dict[str, Any]] = []
    for rel in CLEAN_CORPUS_FILES:
        fp = repo_root / rel
        if not fp.exists():
            continue
        payload = json.loads(fp.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                if any("\ufffd" in str(t) for t in item.get("emotion_tags", [])):
                    continue
                report = lint_corpus_row(item, mode="runtime")
                row_type = str(item.get("type", "")).strip().lower()
                failed_rules = set(report.failed_rules)
                if report.passed or (row_type == "classical_poem" and failed_rules == {"RULE_C7"}):
                    rows.append(item)

    # Load golden anchor files (pre-curated, bypass runtime lint)
    for rel in GOLDEN_ANCHOR_FILES:
        fp = repo_root / rel
        if not fp.exists():
            continue
        payload = json.loads(fp.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                if any("\ufffd" in str(t) for t in item.get("emotion_tags", [])):
                    continue
                learn_point = str(item.get("learn_point", "")).strip()
                do_not_copy = str(item.get("do_not_copy", "")).strip()
                if len(learn_point) >= 5 and do_not_copy:
                    # Mark with high confidence so they score well in retrieval
                    item = {**item, "profile_confidence": 0.95, "_source_family": "golden_anchor"}
                    rows.append(item)

    return rows


def _normalize_profile_confidence(row: dict[str, Any]) -> float:
    val = row.get("profile_confidence", 1.0)
    try:
        parsed = float(val)
    except (TypeError, ValueError):
        parsed = 1.0
    if parsed < 0.0:
        return 0.0
    if parsed > 1.0:
        return 1.0
    return parsed


def corpus_balance_check(repo_root: Path) -> dict[str, Any]:
    corpus = _load_corpus(repo_root)
    return _corpus_balance_from_rows(corpus)


def _corpus_balance_from_rows(corpus: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {k: 0 for k in MIN_PROFILE_COVERAGE}
    for row in corpus:
        tag = _infer_profile_tag(row)
        if tag in counts:
            counts[tag] += 1

    warnings = []
    for profile_id, minimum in MIN_PROFILE_COVERAGE.items():
        current = counts.get(profile_id, 0)
        if current < minimum:
            warnings.append(
                f"profile={profile_id} current={current} minimum={minimum}"
            )

    return {
        "counts": counts,
        "minimum": dict(MIN_PROFILE_COVERAGE),
        "warnings": warnings,
    }


def _type_allowed(row_type: str, profile_override: str) -> bool:
    """Return False for type/profile combinations that should never mix."""
    if row_type == "classical_poem" and profile_override == "club_dance":
        return False
    return True


def _profile_type_priority(row_type: str, profile_override: str) -> int:
    """Lower value means higher retrieval priority for the active profile."""
    if profile_override == "classical_restraint":
        return 0 if row_type == "classical_poem" else 1
    return 0


def retrieve_few_shot_examples(
    user_input: UserInput,
    *,
    repo_root: Path,
    top_k: int = 3,
    return_metadata: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    corpus = _load_corpus(repo_root)
    if not corpus:
        raise InsufficientQualityFewShotError(
            "insufficient quality few-shot samples after pre-injection validation"
        )

    intent_tokens = set(_tokenize(user_input.raw_intent))
    hint_tokens = set(_tokenize(" ".join([user_input.genre_hint, user_input.mood_hint]).strip()))

    scored: list[tuple[int, dict[str, Any]]] = []
    for row in corpus:
        content = str(row.get("content", ""))
        title = str(row.get("title", ""))
        tags = row.get("emotion_tags", [])
        tags_text = " ".join([str(x) for x in tags])
        row_tokens = set(_tokenize(" ".join([title, content, tags_text])))
        score = len(intent_tokens & row_tokens) * 3 + len(hint_tokens & row_tokens)
        scored.append((score, row))

    scored.sort(
        key=lambda x: (
            -x[0],
            _profile_type_priority(
                str(x[1].get("type", "")).strip().lower(),
                str(user_input.profile_override or "").strip(),
            ),
        )
    )

    def _quality_pass(row: dict[str, Any]) -> bool:
        learn_point = str(row.get("learn_point", "")).strip()
        row_type = str(row.get("type", "")).strip().lower()
        if row_type == "modern_lyric":
            # 50-char minimum filters placeholder learn_points for modern lyrics
            # (e.g. "通过意象并置与留白转折完成情绪抬升" = 18 chars is a known placeholder)
            if len(learn_point) < 50:
                return False
            do_not_copy = str(row.get("do_not_copy", "")).strip()
            if not do_not_copy:
                return False
        else:
            # Classical poems: lower bar, no do_not_copy required
            if len(learn_point) < 5:
                return False
        return True

    selected: list[dict[str, Any]] = []
    target_max = max(2, min(top_k, 3))
    fallback_level = "none"
    fallback_reason = "none"

    profile_override = str(user_input.profile_override or "").strip()
    if profile_override in PROFILE_IDS:
        override_candidates: list[dict[str, Any]] = []
        for _, row in scored:
            row_type = str(row.get("type", "")).strip().lower()
            if not _type_allowed(row_type, profile_override):
                continue
            if _infer_profile_tag(row) != profile_override:
                continue
            if not _quality_pass(row):
                continue
            override_candidates.append(row)

        override_selected = sorted(
            override_candidates,
            key=lambda row: _profile_type_priority(
                str(row.get("type", "")).strip().lower(),
                profile_override,
            ),
        )
        if len(override_selected) > target_max:
            override_selected = override_selected[:target_max]

        if len(override_selected) >= 2:
            selected = override_selected
            fallback_level = "override_profile_only"
            fallback_reason = "none"
        else:
            fallback_level = "fallback_to_global"
            fallback_reason = "override_profile_insufficient"

    if not selected:
        for _, row in scored:
            row_type = str(row.get("type", "")).strip().lower()
            if not _type_allowed(row_type, profile_override):
                continue
            if not _quality_pass(row):
                continue
            selected.append(row)
            if len(selected) >= target_max:
                break

    if fallback_level == "fallback_to_global" and not str(fallback_reason).strip():
        fallback_reason = (
            "override_profile_insufficient"
            if profile_override in PROFILE_IDS
            else "global_quality_selection"
        )

    if len(selected) < 2:
        raise InsufficientQualityFewShotError(
            "insufficient quality few-shot samples after pre-injection validation"
        )

    normalized: list[dict[str, Any]] = []
    for row in selected:
        profile_tag = _infer_profile_tag(row)
        raw_source_id = str(row.get("source_id", ""))
        encoded_source_id = urllib.parse.quote(raw_source_id, safe="-_/:.")
        normalized.append(
            {
                "source_id": encoded_source_id,
                "type": str(row.get("type", "modern_lyric")),
                "title": str(row.get("title", "")),
                "emotion_tags_matched": [str(x) for x in row.get("emotion_tags", [])[:4]],
                "profile_tag": profile_tag,
                "profile_confidence": _normalize_profile_confidence(row),
                "content": str(row.get("content", "")),
                "learn_point": str(row.get("learn_point", "")).strip(),
                "do_not_copy": str(row.get("do_not_copy", "")).strip(),
            }
        )

    if not return_metadata:
        return normalized

    votes = Counter(
        sample["profile_tag"]
        for sample in normalized
        if sample.get("profile_tag") in PROFILE_IDS
    )
    if votes:
        profile_vote, vote_count = votes.most_common(1)[0]
        vote_confidence = vote_count / max(len(normalized), 1)
    else:
        profile_vote = ""
        vote_confidence = 0.0

    monoculture_risk = False
    if len(votes) == 1 and normalized:
        dominant = profile_vote
        confidences = [
            float(sample.get("profile_confidence", 0.0) or 0.0)
            for sample in normalized
            if sample.get("profile_tag") == dominant
        ]
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
        monoculture_risk = avg_confidence < 0.67

    return {
        "samples": normalized,
        "profile_vote": profile_vote,
        "vote_confidence": vote_confidence,
        "profile_vote_counts": dict(votes),
        "corpus_balance": _corpus_balance_from_rows(corpus),
        "corpus_monoculture_risk": monoculture_risk,
        "fallback_level": fallback_level,
        "fallback_reason": fallback_reason,
    }
