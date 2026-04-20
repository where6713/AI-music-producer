from __future__ import annotations

from pathlib import Path


def test_gate_g4_detects_invalid_delivery_path() -> None:
    from src.producer_tools.self_check.gate_g4 import validate_docs_alignment

    result = validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD_v2.0.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "delivery_files": [
                "out/lyrics.txt",
                "out/style.txt",
                "docs/out/exclude.txt",
            ],
            "field_name_conflicts": [],
        }
    )

    assert result["status"] == "fail"
    assert "delivery_files" in result["failed_checks"]


def test_gate_g4_passes_for_current_doc_contract() -> None:
    from src.producer_tools.self_check.gate_g4 import validate_docs_alignment

    result = validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD_v2.0.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "delivery_files": [
                "out/lyrics.txt",
                "out/style.txt",
                "out/exclude.txt",
            ],
            "field_name_conflicts": [],
        }
    )

    assert result["status"] == "pass"
    assert result["failed_checks"] == []
