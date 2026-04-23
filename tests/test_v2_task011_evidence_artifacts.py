from __future__ import annotations

from pathlib import Path


def test_task011_blind_review_contains_required_metadata() -> None:
    content = Path("out/task011_ac29_blind_review.md").read_text(encoding="utf-8")
    assert "评审角色" in content
    assert "评审时间" in content
    assert "样本路径" in content
    assert "评分记录" in content
