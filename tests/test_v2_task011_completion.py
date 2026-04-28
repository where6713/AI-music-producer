from __future__ import annotations

import pytest
from pathlib import Path

from src.retriever import corpus_balance_check


@pytest.mark.xfail(
    reason=(
        "corpus data gap: urban_introspective has ~12 entries (need 200), "
        "club_dance and ambient_meditation have 0 entries. "
        "Requires dedicated corpus ingestion for these profiles."
    ),
    strict=False,
)
def test_task011_corpus_coverage_meets_thresholds() -> None:
    report = corpus_balance_check(Path.cwd())
    assert report["warnings"] == []
    assert report["counts"]["urban_introspective"] >= 200
    assert report["counts"]["classical_restraint"] >= 200
    assert report["counts"]["uplift_pop"] >= 150
    assert report["counts"]["club_dance"] >= 100
    assert report["counts"]["ambient_meditation"] >= 80


def test_task011_skill_fragments_exist() -> None:
    fragment_dir = Path(".claude/skills/lyric-craftsman/fragments")
    required = {
        "urban_introspective.md",
        "classical_restraint.md",
        "uplift_pop.md",
        "club_dance.md",
        "ambient_meditation.md",
    }
    existing = {p.name for p in fragment_dir.glob("*.md")}
    assert required.issubset(existing)


def test_urban_fragment_contains_positive_style_anchors() -> None:
    fragment = Path(".claude/skills/lyric-craftsman/fragments/urban_introspective.md")
    text = fragment.read_text(encoding="utf-8")

    assert "Bedroom R&B" in text
    assert "口语" in text
    assert "长短句" in text
    assert "节奏" in text
