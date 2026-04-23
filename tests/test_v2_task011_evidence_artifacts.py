from __future__ import annotations

from pathlib import Path
import json


def test_task011_blind_review_contains_required_metadata() -> None:
    content = Path("out/task011_ac29_blind_review.md").read_text(encoding="utf-8")
    assert "评审角色" in content
    assert "评审时间" in content
    assert "样本路径" in content
    assert "评分记录" in content


def test_task011_human_blind_review_raw_schema() -> None:
    payload = json.loads(Path("out/task011_ac29_human_raw.json").read_text(encoding="utf-8"))
    assert isinstance(payload.get("review_time"), str)
    reviewers = payload.get("reviewers", [])
    samples = payload.get("samples", [])
    reviews = payload.get("reviews", [])
    summary = payload.get("summary", {})
    assert isinstance(reviewers, list) and len(reviewers) >= 3
    assert isinstance(samples, list) and len(samples) == 5
    assert isinstance(reviews, list) and len(reviews) == 5
    assert summary.get("passed", 0) >= 4
