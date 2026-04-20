from __future__ import annotations

from pathlib import Path
from typing import Any


REQUIRED_DOC_PATHS = {
    "prd_path": "AI-music-producer PRD_v1.1.md",
    "pm_role_path": "docs/pm/PM_ROLE.md",
    "pm_rules_path": "docs/pm/PM_RULES.md",
}

REQUIRED_ROOT_DELIVERABLES = {
    "OUTPUT_DEMO_PROMPT.md",
    "PM_AUDIT_REPORT.md",
}


def _normalize_path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().replace("\\", "/")


def validate_docs_alignment(payload: dict[str, Any]) -> dict[str, Any]:
    failed_checks: list[str] = []
    warnings: list[str] = []

    normalized_doc_paths = {
        key: _normalize_path(payload.get(key, "")) for key in REQUIRED_DOC_PATHS
    }

    for key, expected in REQUIRED_DOC_PATHS.items():
        if normalized_doc_paths.get(key) != expected:
            failed_checks.append(key)

    delivery_files_raw = payload.get("delivery_files", [])
    delivery_files = []
    if isinstance(delivery_files_raw, list):
        delivery_files = [
            _normalize_path(item)
            for item in delivery_files_raw
            if isinstance(item, str) and _normalize_path(item)
        ]

    root_delivery_names = {
        Path(item).name for item in delivery_files if "/" not in item and item
    }
    if not REQUIRED_ROOT_DELIVERABLES.issubset(root_delivery_names):
        failed_checks.append("delivery_files")

    field_name_conflicts = payload.get("field_name_conflicts", [])
    if not isinstance(field_name_conflicts, list):
        failed_checks.append("field_name_conflicts")
    elif any(isinstance(x, str) and x.strip() for x in field_name_conflicts):
        failed_checks.append("field_name_conflicts")

    status = "pass" if not failed_checks else "fail"
    if status == "fail" and "delivery_files" in failed_checks:
        warnings.append(
            "Root delivery files must include OUTPUT_DEMO_PROMPT.md and PM_AUDIT_REPORT.md"
        )

    return {
        "status": status,
        "required_doc_paths": REQUIRED_DOC_PATHS,
        "required_root_deliverables": sorted(REQUIRED_ROOT_DELIVERABLES),
        "failed_checks": failed_checks,
        "warnings": warnings,
        "payload": payload,
    }
