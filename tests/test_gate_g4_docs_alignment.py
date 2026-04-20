from __future__ import annotations

from pathlib import Path


def test_gate_g4_detects_invalid_delivery_path() -> None:
    from src.producer_tools.self_check.gate_g4 import validate_docs_alignment

    result = validate_docs_alignment(
        {
            "prd_path": "AI-music-producer PRD_v1.1.md",
            "pm_role_path": "docs/pm/PM_ROLE.md",
            "pm_rules_path": "docs/pm/PM_RULES.md",
            "delivery_files": [
                "docs/OUTPUT_DEMO_PROMPT.md",
                "PM_AUDIT_REPORT.md",
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
            "prd_path": "AI-music-producer PRD_v1.1.md",
            "pm_role_path": "docs/pm/PM_ROLE.md",
            "pm_rules_path": "docs/pm/PM_RULES.md",
            "delivery_files": [
                "OUTPUT_DEMO_PROMPT.md",
                "PM_AUDIT_REPORT.md",
            ],
            "field_name_conflicts": [],
        }
    )

    assert result["status"] == "pass"
    assert result["failed_checks"] == []
