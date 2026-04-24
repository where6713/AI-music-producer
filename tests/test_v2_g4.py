from __future__ import annotations

from src.producer_tools.self_check.gate_g4 import validate_docs_alignment


def test_validate_docs_alignment_pass_with_manifest_path() -> None:
    result = validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "manifest_path": "docs/ai_doc_manifest.json",
            "delivery_files": ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"],
            "field_name_conflicts": [],
        }
    )

    assert result["status"] == "pass"
    assert result["failed_checks"] == []


def test_validate_docs_alignment_fail_without_manifest_path() -> None:
    result = validate_docs_alignment(
        {
            "prd_path": "docs/映月工厂_极简歌词工坊_PRD.json",
            "pm_role_path": "one law.md",
            "pm_rules_path": "目录框架规范.md",
            "delivery_files": ["out/lyrics.txt", "out/style.txt", "out/exclude.txt"],
            "field_name_conflicts": [],
        }
    )

    assert result["status"] == "fail"
    assert "manifest_path" in result["failed_checks"]
