from __future__ import annotations

from typing import Any


REQUIRED_DOC_PATHS = {
    "prd_path": "docs/映月工厂_极简歌词工坊_PRD_v2.0.json",
    "pm_role_path": "one law.md",
    "pm_rules_path": "目录框架规范.md",
}

REQUIRED_OUTPUT_DELIVERABLES = {
    "out/lyrics.txt",
    "out/style.txt",
    "out/exclude.txt",
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

    delivery_paths = {item for item in delivery_files if item}
    if not REQUIRED_OUTPUT_DELIVERABLES.issubset(delivery_paths):
        failed_checks.append("delivery_files")

    field_name_conflicts = payload.get("field_name_conflicts", [])
    if not isinstance(field_name_conflicts, list):
        failed_checks.append("field_name_conflicts")
    elif any(isinstance(x, str) and x.strip() for x in field_name_conflicts):
        failed_checks.append("field_name_conflicts")

    status = "pass" if not failed_checks else "fail"
    if status == "fail" and "delivery_files" in failed_checks:
        warnings.append(
            "Delivery files must include out/lyrics.txt, out/style.txt, and out/exclude.txt"
        )

    return {
        "status": status,
        "required_doc_paths": REQUIRED_DOC_PATHS,
        "required_output_deliverables": sorted(REQUIRED_OUTPUT_DELIVERABLES),
        "failed_checks": failed_checks,
        "warnings": warnings,
        "payload": payload,
    }
