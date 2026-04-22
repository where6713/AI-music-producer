from __future__ import annotations

import json
from pathlib import Path


def test_rectification_task_plan_matches_pm_baseline() -> None:
    task_plan = json.loads(Path("docs/整改task.json").read_text(encoding="utf-8"))

    pm_binding = task_plan.get("PM_测试成功标准_绑定", {})
    assert pm_binding.get("single_source") == "docs/🎵 AI 音乐生成系统产品经理 (PM) Role & Rule.md"

    must_rules = pm_binding.get("必须同时成立", [])
    assert "pm-audit 命令通过" in must_rules
    assert "禁止 Mock 数据与旁路脚本证据" in must_rules

    patch_ids = {item.get("patch_id") for item in task_plan.get("patch_list", [])}
    assert "P-011-10" in patch_ids
    assert "P-011-11" in patch_ids

    acceptance = task_plan.get("新增_AC", {})
    assert "AC_34" in acceptance
    assert "AC_35" in acceptance

    execution = task_plan.get("执行顺序", [])
    assert any("AC-25 至 AC-35" in step for step in execution)
